import sys
import os
import asyncio
import json
import unittest

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.registry import registry
from tools.bridge import bridge_manager, event_queue_var

class TestWindowTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.queue = asyncio.Queue()
        self.token = event_queue_var.set(self.queue)

    async def asyncTearDown(self):
        event_queue_var.reset(self.token)

    async def test_window_list_bridge_payload(self):
        # 1. Call window_list tool in a background task
        tool_task = asyncio.create_task(registry.execute("window_list"))

        # 2. Extract SSE event yielded by bridge
        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        
        self.assertEqual(payload["type"], "bridge_request")
        self.assertEqual(payload["op"], "window:list")
        self.assertEqual(payload["args"], {})
        
        # 3. Simulate resolve callback
        await bridge_manager.resolve_request(payload["id"], {
            "data": [
                {"handle": 111, "title": "Chrome", "process_name": "chrome.exe", "process_id": 12, "is_minimized": False, "is_maximized": False}
            ]
        })
        
        # 4. Verify tool output formatting
        result = await tool_task
        self.assertIn("Title: 'Chrome'", result)
        self.assertIn("Handle: 111", result)

    async def test_window_control_focus(self):
        tool_task = asyncio.create_task(registry.execute("window_control", handle=111, action="focus"))

        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        
        self.assertEqual(payload["type"], "bridge_request")
        self.assertEqual(payload["op"], "window:control")
        self.assertEqual(payload["args"]["handle"], 111)
        self.assertEqual(payload["args"]["action"], "focus")
        
        await bridge_manager.resolve_request(payload["id"], {"data": {"status": "success"}})
        result = await tool_task
        self.assertIn("Successfully executed action 'focus' on window handle 111", result)

    async def test_window_control_moveresize(self):
        tool_task = asyncio.create_task(registry.execute(
            "window_control", handle=111, action="moveresize", x=50, y=50, width=500, height=400
        ))

        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        
        self.assertEqual(payload["args"]["x"], 50)
        self.assertEqual(payload["args"]["y"], 50)
        self.assertEqual(payload["args"]["width"], 500)
        self.assertEqual(payload["args"]["height"], 400)
        
        await bridge_manager.resolve_request(payload["id"], {"data": {"status": "success"}})
        await tool_task

    async def test_clipboard_read(self):
        tool_task = asyncio.create_task(registry.execute("clipboard_read"))
        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        self.assertEqual(payload["op"], "clipboard:read")
        
        await bridge_manager.resolve_request(payload["id"], {"data": "copied text"})
        res = await tool_task
        self.assertEqual(res, "copied text")

    async def test_clipboard_write(self):
        tool_task = asyncio.create_task(registry.execute("clipboard_write", content="new clipboard content"))
        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        self.assertEqual(payload["op"], "clipboard:write")
        self.assertEqual(payload["args"]["content"], "new clipboard content")
        
        await bridge_manager.resolve_request(payload["id"], {"data": {"status": "success"}})
        res = await tool_task
        self.assertIn("Successfully copied text to system clipboard", res)

    async def test_system_notify(self):
        tool_task = asyncio.create_task(registry.execute("system_notify", body="Build Finished", title="Compiler"))
        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        self.assertEqual(payload["op"], "system:notify")
        self.assertEqual(payload["args"]["title"], "Compiler")
        self.assertEqual(payload["args"]["body"], "Build Finished")
        
        await bridge_manager.resolve_request(payload["id"], {"data": {"status": "success"}})
        res = await tool_task
        self.assertIn("System notification pushed successfully", res)

    async def test_fs_select_file(self):
        tool_task = asyncio.create_task(registry.execute("fs_select_file"))
        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        self.assertEqual(payload["op"], "dialog:select_file")
        
        await bridge_manager.resolve_request(payload["id"], {"data": "C:\\notes.txt"})
        res = await tool_task
        self.assertIn("Selected file path: C:\\notes.txt", res)

    async def test_fs_select_folder(self):
        tool_task = asyncio.create_task(registry.execute("fs_select_folder"))
        packet = await self.queue.get()
        payload = json.loads(packet.strip().replace("data:", "").strip())
        self.assertEqual(payload["op"], "dialog:select_folder")
        
        await bridge_manager.resolve_request(payload["id"], {"data": "C:\\MyFolder"})
        res = await tool_task
        self.assertIn("Selected folder path: C:\\MyFolder", res)

if __name__ == "__main__":
    unittest.main()
