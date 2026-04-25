import aiohttp
import asyncio
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
import os

class MuapiClient:
    def __init__(self):
        self.api_key = os.getenv("MUAPI_API_KEY")
        self.base_url = "https://api.muapi.ai/api/v1"
        self.timeout = aiohttp.ClientTimeout(total=120)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_image(self, prompt: str, model: str = "flux-dev", 
                            aspect_ratio: str = "1:1", quality: str = "high",
                            negative_prompt: Optional[str] = None) -> str:
        """Генерация изображения с поддержкой 50+ моделей"""
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # Подготовка данных
            data = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "quality": quality,
                "model": model
            }
            if negative_prompt:
                data["negative_prompt"] = negative_prompt
            
            # Запуск генерации
            async with session.post(
                f"{self.base_url}/{model}",
                json=data,
                headers={"x-api-key": self.api_key, "Content-Type": "application/json"}
            ) as resp:
                result = await resp.json()
                request_id = result.get("id")
                logger.info(f"Started generation {request_id} with model {model}")
            
            # Polling результата
            for attempt in range(45):  # максимум ~2 минуты
                await asyncio.sleep(3)
                async with session.get(
                    f"{self.base_url}/predictions/{request_id}/result",
                    headers={"x-api-key": self.api_key}
                ) as poll_resp:
                    if poll_resp.status == 200:
                        data = await poll_resp.json()
                        if data.get("status") == "completed":
                            output = data.get("output", [])
                            if output:
                                logger.success(f"Generation {request_id} completed")
                                return output[0]  # URL изображения
                    
                    elif poll_resp.status == 404:
                        continue
            
            raise Exception(f"Timeout: generation {request_id} took too long")
    
    @retry(stop=stop_after_attempt(2))
    async def generate_video(self, prompt: str, model: str = "kling-v3",
                            duration: int = 5, aspect_ratio: str = "16:9",
                            image_url: Optional[str] = None) -> str:
        """Генерация видео (текст или изображение -> видео)"""
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            data = {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "model": model
            }
            if image_url:
                data["image_url"] = image_url
            
            async with session.post(
                f"{self.base_url}/{model}",
                json=data,
                headers={"x-api-key": self.api_key}
            ) as resp:
                result = await resp.json()
                request_id = result.get("id")
            
            # Видео генерируется дольше
            for attempt in range(90):  # до 4-5 минут
                await asyncio.sleep(4)
                async with session.get(
                    f"{self.base_url}/predictions/{request_id}/result",
                    headers={"x-api-key": self.api_key}
                ) as poll_resp:
                    if poll_resp.status == 200:
                        data = await poll_resp.json()
                        if data.get("status") == "completed":
                            return data["output"][0]
            
            raise Exception(f"Video generation timeout")
    
    async def lipsync(self, image_url: str, audio_url: str, 
                     model: str = "infinitetalk-image-to-video",
                     resolution: str = "720p") -> str:
        """Lip sync: фото/видео + аудио -> говорящее видео"""
        
        async with aiohttp.ClientSession() as session:
            data = {
                "image_url": image_url,
                "audio_url": audio_url,
                "resolution": resolution,
                "model": model
            }
            
            async with session.post(
                f"{self.base_url}/{model}",
                json=data,
                headers={"x-api-key": self.api_key}
            ) as resp:
                result = await resp.json()
                request_id = result.get("id")
            
            for attempt in range(60):
                await asyncio.sleep(3)
                async with session.get(
                    f"{self.base_url}/predictions/{request_id}/result",
                    headers={"x-api-key": self.api_key}
                ) as poll_resp:
                    if poll_resp.status == 200:
                        data = await poll_resp.json()
                        if data.get("status") == "completed":
                            return data["output"][0]
            
            raise Exception("Lip sync timeout")
    
    async def multi_image_edit(self, prompt: str, image_urls: List[str],
                              model: str = "nano-banana-2-edit") -> str:
        """Редактирование с несколькими референсами (до 14 изображений)"""
        
        async with aiohttp.ClientSession() as session:
            data = {
                "prompt": prompt,
                "images_list": image_urls,
                "model": model
            }
            
            async with session.post(
                f"{self.base_url}/{model}",
                json=data,
                headers={"x-api-key": self.api_key}
            ) as resp:
                result = await resp.json()
                request_id = result.get("id")
            
            for attempt in range(45):
                await asyncio.sleep(3)
                async with session.get(
                    f"{self.base_url}/predictions/{request_id}/result",
                    headers={"x-api-key": self.api_key}
                ) as poll_resp:
                    if poll_resp.status == 200:
                        data = await poll_resp.json()
                        if data.get("status") == "completed":
                            return data["output"][0]
            
            raise Exception("Multi-image edit timeout")
    
    async def upload_file(self, file_data: bytes, filename: str) -> str:
        """Загрузка файла на сервер Muapi"""
        
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('file', file_data, filename=filename)
            
            async with session.post(
                f"{self.base_url}/upload_file",
                data=form,
                headers={"x-api-key": self.api_key}
            ) as resp:
                result = await resp.json()
                return result.get("url")

# Синглтон
muapi = MuapiClient()
