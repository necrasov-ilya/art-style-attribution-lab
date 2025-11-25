"""ComfyUI API client for image generation.

This module handles all communication with a local ComfyUI instance.
It manages workflow execution, polling for results, and image retrieval.
"""
import asyncio
import json
import logging
import random
import uuid
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ComfyUIError(Exception):
    """Exception raised when ComfyUI operation fails."""
    pass


class ComfyUIClient:
    """Async client for ComfyUI API."""
    
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or settings.COMFYUI_BASE_URL).rstrip("/")
        self.timeout = settings.COMFYUI_TIMEOUT
        self.client_id = str(uuid.uuid4())
    
    async def is_available(self) -> bool:
        """Check if ComfyUI is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/system_stats")
                return response.status_code == 200
        except Exception:
            return False
    
    async def queue_prompt(self, workflow: dict) -> str:
        """Queue a workflow for execution.
        
        Args:
            workflow: The workflow dict with prompt data
            
        Returns:
            prompt_id for tracking the execution
            
        Raises:
            ComfyUIError: If queueing fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                payload = {
                    "prompt": workflow,
                    "client_id": self.client_id
                }
                response = await client.post(
                    f"{self.base_url}/prompt",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["prompt_id"]
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                logger.error(f"ComfyUI queue error: {error_detail}")
                raise ComfyUIError(f"Failed to queue prompt: {error_detail}")
            except Exception as e:
                logger.error(f"ComfyUI request failed: {e}")
                raise ComfyUIError(f"ComfyUI request failed: {str(e)}")
    
    async def get_history(self, prompt_id: str) -> Optional[dict]:
        """Get execution history for a prompt.
        
        Args:
            prompt_id: The prompt ID to check
            
        Returns:
            History dict if execution complete, None if still processing
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/history/{prompt_id}")
                response.raise_for_status()
                data = response.json()
                
                if prompt_id in data:
                    return data[prompt_id]
                return None
                
            except Exception as e:
                logger.warning(f"Failed to get history: {e}")
                return None
    
    async def wait_for_completion(
        self, 
        prompt_id: str, 
        poll_interval: float = 1.0
    ) -> dict:
        """Wait for a prompt to complete execution.
        
        Args:
            prompt_id: The prompt ID to wait for
            poll_interval: Seconds between status checks
            
        Returns:
            The completed history entry
            
        Raises:
            ComfyUIError: If execution fails or times out
        """
        elapsed = 0.0
        
        while elapsed < self.timeout:
            history = await self.get_history(prompt_id)
            
            if history is not None:
                # Check for errors in execution
                if "status" in history:
                    status = history["status"]
                    if status.get("status_str") == "error":
                        messages = status.get("messages", [])
                        error_msg = str(messages) if messages else "Unknown error"
                        raise ComfyUIError(f"Execution failed: {error_msg}")
                
                # If we have outputs, execution is complete
                if "outputs" in history and history["outputs"]:
                    return history
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise ComfyUIError(f"Execution timed out after {self.timeout}s")
    
    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download a generated image.
        
        Args:
            filename: Image filename
            subfolder: Subfolder within the output directory
            folder_type: Type of folder (output, input, temp)
            
        Returns:
            Image bytes
            
        Raises:
            ComfyUIError: If download fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": folder_type
                }
                response = await client.get(
                    f"{self.base_url}/view",
                    params=params
                )
                response.raise_for_status()
                return response.content
                
            except Exception as e:
                logger.error(f"Failed to download image: {e}")
                raise ComfyUIError(f"Failed to download image: {str(e)}")
    
    def load_workflow(self, workflow_name: str) -> dict:
        """Load a workflow from the workflows directory.
        
        Args:
            workflow_name: Name of the workflow file (without .json)
            
        Returns:
            Workflow dict
            
        Raises:
            ComfyUIError: If workflow file not found
        """
        workflow_path = settings.WORKFLOWS_DIR / f"{workflow_name}.json"
        
        if not workflow_path.exists():
            raise ComfyUIError(f"Workflow not found: {workflow_path}")
        
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ComfyUIError(f"Invalid workflow JSON: {e}")
    
    def prepare_workflow(
        self,
        workflow: dict,
        positive_prompt: str,
        negative_prompt: str = None,
        seed: int = None,
        batch_size: int = 4,
        checkpoint: str = None
    ) -> dict:
        """Prepare a workflow with custom prompts and settings.
        
        This modifies the workflow dict in place with the provided parameters.
        Assumes standard node IDs from txt2img_style.json workflow.
        
        Args:
            workflow: Base workflow dict
            positive_prompt: The main generation prompt
            negative_prompt: Negative prompt (optional)
            seed: Random seed (optional, will be randomized if not provided)
            batch_size: Number of images to generate
            checkpoint: Checkpoint model name (optional, uses config or workflow default)
            
        Returns:
            Modified workflow dict
        """
        workflow = json.loads(json.dumps(workflow))  # Deep copy
        
        # Set checkpoint model (node 4 - CheckpointLoaderSimple)
        ckpt = checkpoint or settings.COMFYUI_CHECKPOINT
        if ckpt and "4" in workflow:
            workflow["4"]["inputs"]["ckpt_name"] = ckpt
        
        # Set positive prompt (node 6)
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = positive_prompt
        
        # Set negative prompt (node 7)
        if "7" in workflow and negative_prompt:
            workflow["7"]["inputs"]["text"] = negative_prompt
        
        # Set seed (node 3 - KSampler)
        if "3" in workflow:
            workflow["3"]["inputs"]["seed"] = seed if seed else random.randint(0, 2**32 - 1)
        
        # Set batch size (node 5 - EmptyLatentImage)
        if "5" in workflow:
            workflow["5"]["inputs"]["batch_size"] = batch_size
        
        return workflow
    
    def extract_image_filenames(self, history: dict) -> list[str]:
        """Extract generated image filenames from execution history.
        
        Args:
            history: Completed execution history
            
        Returns:
            List of image filenames
        """
        filenames = []
        outputs = history.get("outputs", {})
        
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    if "filename" in img:
                        filenames.append(img["filename"])
        
        return filenames


# Singleton client instance
_client: Optional[ComfyUIClient] = None


def get_comfyui_client() -> ComfyUIClient:
    """Get or create the ComfyUI client singleton."""
    global _client
    if _client is None:
        _client = ComfyUIClient()
    return _client
