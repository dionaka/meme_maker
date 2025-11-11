from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Image, Plain
from PIL import Image as PILImage
import io
from pathlib import Path

# 存储等待图片的用户状态
waiting_users = {}

@register("meme_maker", "Your Name", "图片合成梗图生成器", "1.0.0", "")
class MemeMakerPlugin(Star):
    """梗图生成插件"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 模板路径（template.png 直接在插件根目录）
        self.template_path = Path(__file__).parent / "template.png"
        
        # 检查模板是否存在
        if not self.template_path.exists():
            logger.error(f"[梗图] ❌ 模板不存在: {self.template_path}")
            try:
                plugin_dir = Path(__file__).parent
                files = list(plugin_dir.iterdir())
                logger.error(f"[梗图] 插件目录内容: {[f.name for f in files]}")
            except Exception as e:
                logger.error(f"[梗图] 列出目录失败: {e}")
        else:
            logger.info(f"[梗图] ✅ 模板加载成功: {self.template_path}")
        
        logger.info("梗图生成器插件已加载")
    
    @filter.command("add")
    async def add_command(self, event: AstrMessageEvent):
        """处理 /add 指令"""
        user_id = event.message_obj.sender.user_id
        session_id = event.unified_msg_origin
        
        # 记录用户状态
        waiting_users[user_id] = {
            'session_id': session_id,
            'timestamp': event.message_obj.timestamp
        }
        
        logger.info(f"[梗图] 用户 {user_id} 开始梗图制作流程")
        yield event.plain_result("📷 请发送图片，我将为你生成梗图！")
    
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，处理图片"""
        user_id = event.message_obj.sender.user_id
        
        # 检查用户是否在等待状态
        if user_id not in waiting_users:
            return
        
        logger.info(f"[梗图] 用户 {user_id} 在等待列表中，开始检查消息")
        
        # 提取图片消息
        images = []
        for idx, seg in enumerate(event.message_obj.message):
            if isinstance(seg, Image):
                images.append(seg)
                logger.info(f"[梗图] 找到图片消息段 {idx}")
            elif hasattr(seg, 'type') and seg.type == "image":
                images.append(seg)
                logger.info(f"[梗图] 找到图片消息段 {idx} (通过type)")
        
        if not images:
            logger.info(f"[梗图] 用户 {user_id} 发送的消息中没有图片，继续等待")
            return
        
        logger.info(f"[梗图] 用户 {user_id} 发送了 {len(images)} 张图片，开始处理")
        
        try:
            # 获取第一张图片
            image_seg = images[0]
            
            # 下载图片数据
            image_data = None
            
            # 尝试多种方式获取图片
            if hasattr(image_seg, 'url') and image_seg.url:
                logger.info(f"[梗图] 尝试从 URL 下载: {image_seg.url}")
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_seg.url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            logger.info(f"[梗图] URL 下载成功: {len(image_data)} 字节")
            
            elif hasattr(image_seg, 'file') and image_seg.file:
                logger.info(f"[梗图] 尝试从 file 读取: {image_seg.file}")
                with open(image_seg.file, 'rb') as f:
                    image_data = f.read()
                    logger.info(f"[梗图] file 读取成功: {len(image_data)} 字节")
            
            elif hasattr(image_seg, 'path') and image_seg.path:
                logger.info(f"[梗图] 尝试从 path 读取: {image_seg.path}")
                with open(image_seg.path, 'rb') as f:
                    image_data = f.read()
                    logger.info(f"[梗图] path 读取成功: {len(image_data)} 字节")
            
            elif hasattr(image_seg, 'data'):
                if hasattr(image_seg.data, 'url') and image_seg.data.url:
                    logger.info(f"[梗图] 尝试从 data.url 下载: {image_seg.data.url}")
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_seg.data.url) as resp:
                            if resp.status == 200:
                                image_data = await resp.read()
                                logger.info(f"[梗图] data.url 下载成功: {len(image_data)} 字节")
                elif hasattr(image_seg.data, 'file') and image_seg.data.file:
                    logger.info(f"[梗图] 尝试从 data.file 读取: {image_seg.data.file}")
                    with open(image_seg.data.file, 'rb') as f:
                        image_data = f.read()
                        logger.info(f"[梗图] data.file 读取成功: {len(image_data)} 字节")
            
            if not image_data:
                logger.error(f"[梗图] 无法获取图片数据，Image 对象属性: {dir(image_seg)}")
                yield event.plain_result("❌ 图片下载失败，请重试")
                del waiting_users[user_id]
                return
            
            logger.info(f"[梗图] 开始处理图片，大小: {len(image_data)} 字节")
            
            # 检查模板是否存在
            if not self.template_path.exists():
                logger.error(f"[梗图] 模板不存在: {self.template_path}")
                yield event.plain_result(f"❌ 模板图片不存在\n路径: {self.template_path}")
                del waiting_users[user_id]
                return
            
            # 处理图片
            result_image_data = await self.process_image(image_data)
            
            logger.info(f"[梗图] 图片处理完成，结果大小: {len(result_image_data)} 字节")
            
            # 清除用户状态
            del waiting_users[user_id]
            logger.info(f"[梗图] 已清除用户 {user_id} 的等待状态")
            
            # 返回处理后的图片
            result_image = Image.fromBytes(result_image_data)
            yield event.chain_result([Plain("✅ 梗图生成完成！\n"), result_image])
            
        except Exception as e:
            logger.error(f"[梗图] 处理图片时出错: {e}", exc_info=True)
            if user_id in waiting_users:
                del waiting_users[user_id]
            yield event.plain_result(f"❌ 处理失败: {str(e)}")
    
    async def process_image(self, user_image_data: bytes) -> bytes:
        """
        将用户图片合成到模板上（智能裁剪填充）
        
        参数:
            user_image_data: 用户发送的图片数据
        
        返回:
            处理后的图片字节数据
        """
        # 检查模板是否存在
        if not self.template_path.exists():
            raise FileNotFoundError(f"模板图片不存在: {self.template_path}")
        
        # 打开模板和用户图片
        template = PILImage.open(str(self.template_path))
        user_image = PILImage.open(io.BytesIO(user_image_data))
        
        # 转换为 RGB 模式（避免某些图片格式问题）
        if user_image.mode != 'RGB' and user_image.mode != 'RGBA':
            user_image = user_image.convert('RGB')
        
        logger.info(f"[梗图] 模板尺寸: {template.size}, 用户图片尺寸: {user_image.size}")
        
        # ====== 自定义区域 - 根据你的模板修改这些值 ======
        # 定义目标区域：(左上角x, 左上角y, 宽度, 高度)
        target_x = 125         # 目标区域左上角 X 坐标
        target_y = 110         # 目标区域左上角 Y 坐标
        target_width = 400     # 目标区域宽度
        target_height = 400    # 目标区域高度
        
        logger.info(f"[梗图] 目标区域: ({target_x}, {target_y}) 尺寸: {target_width}x{target_height}")
        
        # 🔥 裁剪填充方案 - 完全填充目标区域，自动居中裁剪
        # 计算缩放比例（取较大值以确保完全覆盖）
        scale_x = target_width / user_image.width
        scale_y = target_height / user_image.height
        scale = max(scale_x, scale_y)  # 取大值确保填满
        
        # 计算缩放后尺寸
        new_width = int(user_image.width * scale)
        new_height = int(user_image.height * scale)
        
        logger.info(f"[梗图] 缩放比例: {scale:.2f}, 缩放后尺寸: {new_width}x{new_height}")
        
        # 缩放图片
        user_image = user_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
        
        # 计算裁剪区域（居中裁剪）
        crop_x = (new_width - target_width) // 2
        crop_y = (new_height - target_height) // 2
        
        # 裁剪到目标尺寸
        user_image = user_image.crop((
            crop_x,
            crop_y,
            crop_x + target_width,
            crop_y + target_height
        ))
        
        logger.info(f"[梗图] 最终图片尺寸: {user_image.size}")
        
        # 粘贴到模板
        if user_image.mode == 'RGBA':
            template.paste(user_image, (target_x, target_y), user_image)
        else:
            template.paste(user_image, (target_x, target_y))
        # ====== 自定义区域结束 ======
        
        # 保存结果
        output = io.BytesIO()
        template.save(output, format='PNG')
        output.seek(0)
        
        logger.info("[梗图] 图片保存完成")
        return output.read()
