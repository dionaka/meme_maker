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
        
        # 模板1路径（原有模板）
        self.template_path = Path(__file__).parent / "template.png"
        # 模板2路径（新增透明底模板）
        self.template2_path = Path(__file__).parent / "template2.png"
        
        # 检查模板是否存在
        if not self.template_path.exists():
            logger.error(f"[梗图] ❌ 模板1不存在: {self.template_path}")
        else:
            logger.info(f"[梗图] ✅ 模板1加载成功: {self.template_path}")
            
        if not self.template2_path.exists():
            logger.error(f"[梗图] ❌ 模板2不存在: {self.template2_path}")
        else:
            logger.info(f"[梗图] ✅ 模板2加载成功: {self.template2_path}")
        
        logger.info("梗图生成器插件已加载")
    
    @filter.command("add")
    async def add_command(self, event: AstrMessageEvent):
        """处理 /add 指令（原有功能）"""
        user_id = event.message_obj.sender.user_id
        session_id = event.unified_msg_origin
        
        # 记录用户状态
        waiting_users[user_id] = {
            'session_id': session_id,
            'timestamp': event.message_obj.timestamp,
            'mode': 'add'  # 标记为模式1
        }
        
        logger.info(f"[梗图] 用户 {user_id} 开始梗图制作流程（模式：add）")
        yield event.plain_result("📷 请发送图片，我将为你生成梗图！")
    
    @filter.command("add1")
    async def add1_command(self, event: AstrMessageEvent):
        """处理 /add1 指令（新增功能）"""
        user_id = event.message_obj.sender.user_id
        session_id = event.unified_msg_origin
        
        # 记录用户状态
        waiting_users[user_id] = {
            'session_id': session_id,
            'timestamp': event.message_obj.timestamp,
            'mode': 'add1'  # 标记为模式2
        }
        
        logger.info(f"[梗图] 用户 {user_id} 开始梗图制作流程（模式：add1）")
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
            
            # 获取用户模式
            mode = waiting_users[user_id]['mode']
            
            # 根据模式选择处理方法
            if mode == 'add':
                # 检查模板1是否存在
                if not self.template_path.exists():
                    logger.error(f"[梗图] 模板1不存在: {self.template_path}")
                    yield event.plain_result(f"❌ 模板图片不存在\n路径: {self.template_path}")
                    del waiting_users[user_id]
                    return
                result_image_data = await self.process_image_mode1(image_data)
            else:  # mode == 'add1'
                # 检查模板2是否存在
                if not self.template2_path.exists():
                    logger.error(f"[梗图] 模板2不存在: {self.template2_path}")
                    yield event.plain_result(f"❌ 模板图片不存在\n路径: {self.template2_path}")
                    del waiting_users[user_id]
                    return
                result_image_data = await self.process_image_mode2(image_data)
            
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
    
    async def process_image_mode1(self, user_image_data: bytes) -> bytes:
        """
        模式1：将用户图片合成到模板上（智能裁剪填充）
        原有的 /add 功能
        """
        # 打开模板和用户图片
        template = PILImage.open(str(self.template_path))
        user_image = PILImage.open(io.BytesIO(user_image_data))
        
        # 转换为 RGB 模式
        if user_image.mode != 'RGB' and user_image.mode != 'RGBA':
            user_image = user_image.convert('RGB')
        
        logger.info(f"[梗图] 模板尺寸: {template.size}, 用户图片尺寸: {user_image.size}")
        
        # 定义目标区域
        target_x = 125
        target_y = 105
        target_width = 400
        target_height = 400
        
        # 裁剪填充方案
        scale_x = target_width / user_image.width
        scale_y = target_height / user_image.height
        scale = max(scale_x, scale_y)
        
        new_width = int(user_image.width * scale)
        new_height = int(user_image.height * scale)
        
        user_image = user_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
        
        crop_x = (new_width - target_width) // 2
        crop_y = (new_height - target_height) // 2
        
        user_image = user_image.crop((
            crop_x,
            crop_y,
            crop_x + target_width,
            crop_y + target_height
        ))
        
        # 粘贴到模板
        if user_image.mode == 'RGBA':
            template.paste(user_image, (target_x, target_y), user_image)
        else:
            template.paste(user_image, (target_x, target_y))
        
        # 保存结果
        output = io.BytesIO()
        template.save(output, format='PNG')
        output.seek(0)
        
        return output.read()
    
    async def process_image_mode2(self, user_image_data: bytes) -> bytes:
        """
        模式2：将透明底模板覆盖在用户图片上
        新增的 /add1 功能
        
        策略：
        1. 将用户图片等比缩放到模板尺寸（1990x1918）
        2. 将模板（透明底）叠加在用户图片上
        """
        # 打开用户图片和模板
        user_image = PILImage.open(io.BytesIO(user_image_data))
        template = PILImage.open(str(self.template2_path))
        
        logger.info(f"[梗图Mode2] 用户图片尺寸: {user_image.size}, 模板尺寸: {template.size}")
        
        # 转换用户图片为 RGBA 模式（支持透明度）
        if user_image.mode != 'RGBA':
            user_image = user_image.convert('RGBA')
        
        # 确保模板也是 RGBA 模式
        if template.mode != 'RGBA':
            template = template.convert('RGBA')
        
        # 获取模板尺寸
        template_width, template_height = template.size
        
        # 🔥 智能缩放用户图片到模板尺寸（保持比例，裁剪填充）
        scale_x = template_width / user_image.width
        scale_y = template_height / user_image.height
        scale = max(scale_x, scale_y)  # 取大值确保填满
        
        new_width = int(user_image.width * scale)
        new_height = int(user_image.height * scale)
        
        logger.info(f"[梗图Mode2] 缩放比例: {scale:.2f}, 缩放后尺寸: {new_width}x{new_height}")
        
        # 缩放用户图片
        user_image = user_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
        
        # 居中裁剪到模板尺寸
        crop_x = (new_width - template_width) // 2
        crop_y = (new_height - template_height) // 2
        
        user_image = user_image.crop((
            crop_x,
            crop_y,
            crop_x + template_width,
            crop_y + template_height
        ))
        
        logger.info(f"[梗图Mode2] 最终用户图片尺寸: {user_image.size}")
        
        # 🔥 将模板叠加到用户图片上（透明底会显示底层用户图片）
        # 创建结果画布
        result = user_image.copy()
        
        # 使用 alpha_composite 进行透明叠加
        result = PILImage.alpha_composite(result, template)
        
        # 保存结果
        output = io.BytesIO()
        result.save(output, format='PNG')
        output.seek(0)
        
        logger.info("[梗图Mode2] 图片保存完成")
        return output.read()
