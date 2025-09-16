from asyncio import Queue
from lib.node.node import PollingNode
from datetime import datetime
from lib import local_config


local_config.readLocalConfig()

runningNodes = {}
notificationQueue = Queue()


globalVarDict = {}
globalVarQueue = Queue()


pollingNodes = []

async def setRunningNode(id: int, value=None) -> int:
    """_summary_

    Args:
        id (int): _description_
        value (_type_, optional): _description_. Defaults to None.

    Returns:
        int: _description_
    """    """_summary_

    Args:
        id (int): _description_
        value (_type_, optional): _description_. Defaults to None.
    """    
    current_time = datetime.now()
    delta = None
    if id in runningNodes and 'timestamp' in runningNodes:
        delta = (current_time - datetime.fromisoformat(runningNodes[id]['timestamp'])).total_seconds()* 1_000_000
    
    data = {
        "value": value,
        "timestamp": current_time.isoformat(),
        "delta": delta
    }
    runningNodes[id] = {"isRunning": "running", "value": data, "timestamp": datetime.now().isoformat()}
    await notificationQueue.put(runningNodes)


async def setStoppingNode(id, value=None):
    current_time = datetime.now()
    delta = None
    if id in runningNodes and 'timestamp' in runningNodes:
        delta = (current_time - datetime.fromisoformat(runningNodes[id]['timestamp'])).total_seconds()* 1_000_000
    
    data = {
        "value": value,
        "timestamp": current_time.isoformat(),
        "delta": delta
    }
    runningNodes[id] = {"isRunning": "not running", "value": data}
    await notificationQueue.put(runningNodes)



async def putGlobalValue(value):
    await globalVarQueue.put(value)
    await PollingNode.broadcast(value)