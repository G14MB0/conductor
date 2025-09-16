import networkx as nx
import matplotlib.pyplot as plt
import asyncio

from lib import global_var as gv
import time
from lib.node import node as N

# Create a NetworkX graph
G = nx.DiGraph()

# Used as starting points for graph
triggersNode = []


def updateNodesAndEdges(data):
    G.clear()
    gv.pollingNodes = []

    # Add nodes
    for node in data["nodes"]:
        if node["type"] == 'TimerNode' and 'timerInterval' in node["data"]: # or node["type"] == 'trigger':
            G.add_node(node["id"], type=node["type"], data=node["data"], position=node['position'], style=node['style'])
        elif (node["type"] == 'FunctionNode' and 'code' in node["data"]) or (node.get('data', {}).get('type') == 'FunctionNode' and 'code' in node["data"]):
            G.add_node(node["id"], type=node["type"], data=node["data"], position=node['position'], style=node['style'])
        elif node["type"] == 'ComparatorNode' and 'code' in node["data"]:
            G.add_node(node["id"], type=node["type"], data=node["data"], position=node['position'], style=node['style'])
        elif node["type"] == 'DebugNode':
            G.add_node(node["id"], type=node["type"], data=node["data"], position=node['position'], style=node['style'])
        elif node["type"] == 'SumNode' or node["type"] == 'MultiplyNode' or node["type"] == 'SubtractNode' or node["type"] == 'DivideNode':
            G.add_node(node["id"], type=node["type"], data=node["data"], position=node['position'], style=node['style'])
        elif node["type"] == 'EqualsNode':
            G.add_node(node["id"], type=node["type"], data=node["data"], position=node['position'], style=node['style'])
        else:
            G.add_node(node["id"], type=node["type"], data=node["data"], position=node['position'], style=node['style'])

    # Add edges
    for edge in data["edges"]:
        G.add_edge(edge["source"], edge["target"], sourceHandle=edge['sourceHandle'], targetHandle=edge['targetHandle'])



def finalizeNodesObject():
    gv.pollingNodes = []
    # Add nodes
    for nodeName in G.nodes:
        node = G.nodes[nodeName]
        if node["type"] == 'TimerNode' and 'timerInterval' in node["data"]: # or node["type"] == 'trigger':
            print("Add Timer Node")
            if 'loop' in node["data"]:
                temp = N.TimerNode(nodeName, node["data"]['timerInterval'], node["data"]['selected'], node["data"]['loop'])
            else:
                temp = N.TimerNode(nodeName, node["data"]['timerInterval'], node["data"]['selected'])
            G.add_node(nodeName, type=node["type"], data=node["data"], position=node['position'], style=node['style'], obj=temp)
        elif (node["type"] == 'FunctionNode' and 'code' in node["data"]) or (node.get('data', {}).get('type') == 'FunctionNode' and 'code' in node["data"]):
            print("Add Function Node")
            temp = N.FunctionNode(nodeName, node["data"]['code'])
            G.add_node(nodeName, type=node["type"], data=node["data"], position=node['position'], style=node['style'], obj=temp)
            if node.get('data', {}).get('isPolling') == 'true':
                print("Add Polling Node")
                gv.pollingNodes.append(N.PollingNode(nodeName, node['data']['replacementKey']))
        elif node["type"] == 'ComparatorNode' and 'code' in node["data"]:
            print("Add Comparator Node")
            temp = N.ComparatorNode(nodeName, node["data"]['code'])
            G.add_node(nodeName, type=node["type"], data=node["data"], position=node['position'], style=node['style'], obj=temp)
        elif node["type"] == 'DebugNode':
            print("Add Debug Node")
            temp  = N.DebugNode(nodeName)
            G.add_node(nodeName, type=node["type"], data=node["data"], position=node['position'], style=node['style'], obj=temp)
        elif node["type"] == 'SumNode' or node["type"] == 'MultiplyNode' or node["type"] == 'SubtractNode' or node["type"] == 'DivideNode':
            print("Add Muxer Node")
            temp  = N.MuxerNode(nodeName, node['data']['operation'])
            G.add_node(nodeName, type=node["type"], data=node["data"], position=node['position'], style=node['style'], obj=temp)
        elif node["type"] == 'EqualsNode':
            print("Add Equals Node")
            temp  = N.EqualsNode(nodeName, node['data']['logic'])
            G.add_node(nodeName, type=node["type"], data=node["data"], position=node['position'], style=node['style'], obj=temp)
        else:
            print(f"adding a node without object: {node['type']}")
            G.add_node(nodeName, type=node["type"], data=node["data"], position=node['position'], style=node['style'])
    return


def deleteNodesObjects():
    for nodeName in G.nodes:
        node = G.nodes[nodeName]
        if "obj" in node: del node["obj"]


def plotGraph():
    nx.draw(G, with_labels=True, node_size=2000, node_color="lightblue", font_weight="bold", arrows=True)
    plt.show()  # Display the plot


def getNodesAndEdges():
    nodes = []
    edges = []

    for node in G.nodes:
        nodeData = G.nodes[node]
        nodes.append({
            "id": nodeData['data']['id'],
            'type': nodeData['type'],
            'data': nodeData['data'],
            'position': nodeData['position'],
            'style': nodeData['style']
                      })
    
    for edge in G.edges:
        edges.append({
            'source': edge[0],
            'target':edge[1],
            'type': 'smoothstep',
            'sourceHandle': G.edges[edge]['sourceHandle'],
            'targetHandle': G.edges[edge]['targetHandle'],
        })

    data = {"nodes": nodes, "edges": edges}

    return data


loop = asyncio.get_event_loop()

def runGraph():
    finalizeNodesObject()
    # Ensure all nodes are set to run
    for node in G.nodes:
        if 'obj' in G.nodes[node]:
            G.nodes[node]['obj'].run = True
    # Schedule the start_graph_execution coroutine without using asyncio.run
    if not loop.is_running():
        loop.run_until_complete(N.start_graph_execution(G))
    else:
        N.tasks.append(loop.create_task(N.start_graph_execution(G)))


def stopGraph():
    for node in G.nodes:
        if 'obj' in G.nodes[node]: 
            print(f"stopping {node}")
            G.nodes[node]['obj'].run = False
    time.sleep(0.5)
    for task in N.tasks:
        if task:
            task.cancel()
    N.tasks = []
    deleteNodesObjects()


