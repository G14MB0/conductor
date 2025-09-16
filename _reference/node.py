import asyncio
from asyncio.exceptions import CancelledError
import re
import traceback
import queue
from lib import global_var as gv
from lib.node import utils
import inspect

# Asyncio tasks
tasks = []



async def execute_successors(graph, node_id, data=None, predecessor=None):
    # global tasks
    # print(f"task created on {node_id} with data {data}")
    # print(".", end="")
    if node_id in graph.nodes:
        if 'obj' in graph.nodes[node_id]:
            node = graph.nodes[node_id]['obj']
            # print(f"executing node {node_id}")
            await node.execute(graph, data, predecessor)  




async def start_graph_execution(graph):
    # Identifica i nodi senza predecessori e avviali in modo asincrono
    initial_nodes = [node for node in graph.nodes if len(list(graph.predecessors(node))) == 0]
    for node_id in initial_nodes:
        task = asyncio.create_task(execute_successors(graph, node_id))
        tasks.append(task)

     # Now, await all tasks to complete. This is where concurrency happens.
    await asyncio.gather(*tasks)
    # for node in list(graph.nodes):
    #     if hasattr(gv, f"{node}_data"):
    #         delattr(gv, f"{node}_data")


class Node:
    def __init__(self, id, type):
        self.id = id
        self.type = type
        self.run = True
        self.output = None

    def execute(self):
        pass  # To be overridden by subclasses


class DebugNode(Node):
    """A function Node extend the Node class as a type: "function"
    
    Define also function: function
    """    
    def __init__(self, id):
        super().__init__(id, "debug")

        # Returns of the funciton

    async def execute(self, graph, data=None, caller=None):
        await gv.setRunningNode(self.id, data)
        await gv.setStoppingNode(self.id, data)


class FunctionNode(Node):
    """A function Node extend the Node class as a type: "function"
    
    Define also function: function
    """    
    def __init__(self, id, code):
        super().__init__(id, "function")

        # Returns of the funciton
        self.output = None
        self.code = code
        

    async def execute(self, graph, data=None, caller=None):
        if self.run:
            await gv.setRunningNode(self.id, self.output)
            try:
                # Use regular expression to extract the function name
                match = re.search(r'def (\w+)\(', self.code)
                if match:
                    self.function_name = match.group(1)
                else:
                    self.function_name = None
                    print("Function name could not be determined.")
                    self.output = "Function name could not be determined."

                # Execute the function definition if a name was found
                if self.function_name:
                    exec(self.code, globals())
                    function_ref = globals().get(self.function_name)
                    if function_ref:
                        # Check if the function is a coroutine function
                        if asyncio.iscoroutinefunction(function_ref):
                            # If it is, await it
                            if data != None:
                                self.output = await function_ref(data)
                            else:
                                sig = inspect.signature(function_ref)
                                if len(sig.parameters) > 0:
                                    self.output = await function_ref(None)
                                else:
                                    self.output = await function_ref()
                            # self.output = await function_ref(data) if data else await function_ref()
                        else:
                            # Call the function normally if it's not async
                            if data:
                                self.output = function_ref(data)
                            else:
                                sig = inspect.signature(function_ref)
                                if len(sig.parameters) > 0:
                                    self.output = function_ref(None)
                                else:
                                    self.output = function_ref()
                    else:
                        print("Function reference not found.")
                        self.output = "Function reference not found."

            except:
                self.output = str(traceback.format_exc())
                await gv.setStoppingNode(self.id, value=self.output)
                # print(traceback.print_exc())
                
            # Procedi con l'esecuzione dei nodi successori sequenzialmente
            successors = list(graph.successors(self.id))
            for successor in successors:
                try:
                    await execute_successors(graph, successor, data=self.output.copy(), predecessor=self.id)  
                except:
                    await execute_successors(graph, successor, data=self.output, predecessor=self.id)  

            await gv.setStoppingNode(self.id, value=self.output)
            return
            
                    



class ComparatorNode(Node):
    def __init__(self, id, code):
        super().__init__(id, "comparator")
        # Returns of the funciton
        self.output = 0
        self.code = code


    async def execute(self, graph, data=None, caller=None):
        if self.run:
            await gv.setRunningNode(self.id, self.output)
            try:
                # Use regular expression to extract the function name
                match = re.search(r'def (\w+)\(', self.code)
                if match:
                    self.function_name = match.group(1)
                else:
                    self.function_name = None
                    print("Function name could not be determined.")

                # Execute the function definition if a name was found
                if self.function_name:
                    exec(self.code, globals())
                    print(f"funciton defined: {self.function_name}")
                    function_ref = globals().get(self.function_name)
                    if function_ref:
                        # Check if the function is a coroutine function
                        if asyncio.iscoroutinefunction(function_ref):
                            # If it is, await it
                            self.output = await function_ref(data) if data else await function_ref()
                        else:
                            # Call the function normally if it's not async
                            self.output = function_ref(data) if data else function_ref()
                    else:
                        print("Function reference not found.")

                if self.output == 0:
                    specific_successors = [successor for successor in graph.successors(self.id)
                                        if graph.get_edge_data(self.id, successor)['sourceHandle'] == 'a']
                else:
                    specific_successors = [successor for successor in graph.successors(self.id)
                                        if graph.get_edge_data(self.id, successor)['sourceHandle'] == 'b']

                await gv.setStoppingNode(self.id, self.output)
                await execute_successors(graph, specific_successors[0], predecessor=self.id)  

            except:
                self.output = str(traceback.format_exc())
                await gv.setStoppingNode(self.id, value=self.output)
                return




class MuxerNode(Node):
    def __init__(self, id, operation):
        super().__init__(id, "muxer")
        self.operation = operation
        self.toOperate = {}
    

    async def operate(self):
        if self.operation == "sum":
            self.output = sum(self.toOperate.values())
        
        if self.operation == "multiply":
            self.output = 1
            for value in self.toOperate.values():
                self.output *= value

        if self.operation == "subtract":
            self.output = self.toOperate['upperNode'] - self.toOperate['lowerNode']

        if self.operation == "divide":
            self.output = self.toOperate['upperNode'] / self.toOperate['lowerNode']


    async def execute(self, graph, data=None, caller=None):
        await gv.setRunningNode(self.id, self.output)
        # Check if caller has been passed
        if caller == None:
            self.output = "ERROR"

        upperNode = [predecessor for predecessor in graph.predecessors(self.id)
                                        if graph.get_edge_data(predecessor, self.id)['targetHandle'] == 'a']
        lowerNode = [predecessor for predecessor in graph.predecessors(self.id)
                                        if graph.get_edge_data(predecessor, self.id)['targetHandle'] == 'b']
        
        if len(upperNode) > 0 and len(lowerNode) > 0:
            upperNode = upperNode[0]
            lowerNode = lowerNode[0]
        else:
            return
        
        # Check if the caller_data g_var exist, if not, set it with value
        l_variable = f"{caller}_data"
        if not hasattr(gv, l_variable) or getattr(gv, l_variable) != data:
            setattr(gv, l_variable, data)

        # Now check if all the predecessors g_var has been initialized, so make the operation, otherwise pass
        for predecessor in list(graph.predecessors(self.id)):
            if not hasattr(gv, f"{predecessor}_data"):
                self.output = None
                return
            else:
                if predecessor == upperNode:
                    self.toOperate["upperNode"] = (getattr(gv, f"{predecessor}_data"))
                elif predecessor == lowerNode:
                    self.toOperate["lowerNode"] = (getattr(gv, f"{predecessor}_data"))
                else:
                    print("Error in caller node.")
                    return

        await self.operate()
        # Procedi con l'esecuzione dei nodi successori sequenzialmente
        successors = list(graph.successors(self.id))
        await gv.setStoppingNode(self.id, self.output)
        for successor in successors:
            await execute_successors(graph, successor, data=self.output, predecessor=self.id)  



class EqualsNode(Node):
    def __init__(self, id, logic):
        super().__init__(id, "equals")
        self.logic = logic
        self.toOperate = {}
    

    async def operate(self):
        if self.logic == "=":
            return "a" if self.toOperate["upperNode"] == self.toOperate["lowerNode"] else "b"
        if self.logic == ">":
            return "a" if self.toOperate["upperNode"] > self.toOperate["lowerNode"] else "b"
        if self.logic == "<":
            return "a" if self.toOperate["upperNode"] < self.toOperate["lowerNode"] else "b"


    async def execute(self, graph, data=None, caller=None):
        try:
            await gv.setRunningNode(self.id, self.output)
            # Check if caller has been passed
            if caller == None:
                self.output = "ERROR"

            upperNode = [predecessor for predecessor in graph.predecessors(self.id)
                                            if graph.get_edge_data(predecessor, self.id)['targetHandle'] == 'a']
            lowerNode = [predecessor for predecessor in graph.predecessors(self.id)
                                            if graph.get_edge_data(predecessor, self.id)['targetHandle'] == 'b']
            
            if len(upperNode) > 0 and len(lowerNode) > 0:
                upperNode = upperNode[0]
                lowerNode = lowerNode[0]
            else:
                return
            
            # Check if the caller_data g_var exist, if not, or its value is changed, set it with new value
            l_variable = f"{caller}_data"
            if not hasattr(gv, l_variable) or getattr(gv, l_variable) != data:
                setattr(gv, l_variable, data)

            # Now check if all the predecessors g_var has been initialized, so make the operation, otherwise pass
            for predecessor in list(graph.predecessors(self.id)):
                if not hasattr(gv, f"{predecessor}_data"):
                    self.output = None
                    return
                else:
                    if predecessor == upperNode:
                        self.toOperate["upperNode"] = (getattr(gv, f"{predecessor}_data"))
                    elif predecessor == lowerNode:
                        self.toOperate["lowerNode"] = (getattr(gv, f"{predecessor}_data"))
                    else:
                        print("Error in caller node.")
                        return
        except:
            self.output = traceback.format_exc()
            print(traceback.print_exc())


        outputNode = await self.operate()
        self.output = self.toOperate
        # Procedi con l'esecuzione dei nodi successori sequenzialmente
        await gv.setStoppingNode(self.id, self.output)

        specific_successors = [successor for successor in graph.successors(self.id)
                            if graph.get_edge_data(self.id, successor)['sourceHandle'] == outputNode]
        

        if len(specific_successors) > 0:
            for successor in specific_successors:
                await gv.setStoppingNode(self.id, self.output)
                task = asyncio.create_task(execute_successors(graph, successor, data=self.output.copy(), predecessor=self.id))
                tasks.append(task)


class TimerNode(Node):
    def __init__(self, id, value, mu, loop=False):
        super().__init__(id, "timer")
        self.value = float(value)

        # Set the gv.biggerTimerValue as the greater timer
        if not hasattr(gv, "biggerTimerValue"):
            setattr(gv, "biggerTimerValue", self.value)
        else:
            if getattr(gv, "biggerTimerValue") < self.value:
                setattr(gv, "biggerTimerValue", self.value)

        self.delay = 0
        self.mu = mu
        self.loop = loop


    async def waitTimer(self):
        try:
            self.delay = self.value
            if self.mu == "m":
                self.delay *= 60
            elif self.mu == "h":
                self.delay *= 3600
            await asyncio.sleep(self.delay)
            return
        except CancelledError:
            self.run = False


    async def execute(self, graph, data=None, caller=None):
        counter = 0
        while self.run:
            await gv.setRunningNode(self.id, self.output)
            # print(f"Starting Timer {self.id}")
            await self.waitTimer()
            # print(f"Timer {self.id} finished.")

            counter += 1*self.delay
            self.output = counter
            # Procedi con l'esecuzione dei nodi successori sequenzialmente
            successors = list(graph.successors(self.id))
            for successor in successors:
                await gv.setStoppingNode(self.id, self.output)
                task = asyncio.create_task(execute_successors(graph, successor, data=counter, predecessor=self.id))
                tasks.append(task)

            
            if not self.loop:
                await gv.setStoppingNode(self.id, self.output)
                break
        
        await gv.setStoppingNode(self.id, self.output)
        



class PollingNode(Node):
    """
    The PollingNode is a special Class that is executed any time gv.putGlobalValue({name: value}) is called.
    this can be done by a function node for example!
    if you call that method, all the node connected to the PollingNode that are called only if the value updated is equals to globalVarToPoll with that value as output.
    To add a PollinNode simply specify it in the NodeDefiniton.js

    Args:
        Node (_type_): _description_
    """    
    def __init__(self, id, globalVar):
        super().__init__(id, "polling")
        self.globalVarToPoll = globalVar

    @classmethod
    async def broadcast(cls, value):
        """Broadcast the value to all nodes."""
        for node in gv.pollingNodes:
            # You might want to make this part asynchronous or handle it differently
            await node.handle_value(value)

    async def handle_value(self, value):
        """Handle the received value."""
        if next(iter(value.keys())) == self.globalVarToPoll:
            await self.execute(utils.G, value)

    async def execute(self, graph, value):
        try:
            successors = list(graph.successors(self.id))
            for successor in successors:
                task = asyncio.create_task(execute_successors(graph, successor, data=next(iter(value.values())), predecessor=self.id))
                tasks.append(task)
        except:
            pass



