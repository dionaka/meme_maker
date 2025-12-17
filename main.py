from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Image, Plain
from PIL import Image as PILImage
import io
from pathlib import Path
import cv2
import numpy as np

# 存储等待图片的用户状态
waiting_users = {}

@register("meme_maker", "Your Name", "图片合成梗图生成器", "1.0.0", "")
class MemeMakerPlugin(Star):
    """梗图生成插件"""
    
    def __init__(self, context: Context):
        #初始化
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
    
    @filter.command("add2")
    async def add2_command(self, event: AstrMessageEvent):
        """处理 /add2 指令（圣诞帽功能）"""
        user_id = event.message_obj.sender.user_id
        session_id = event.unified_msg_origin
    
        # 记录用户状态，模式标记为 'add2'
        waiting_users[user_id] = {
            'session_id': session_id,
            'timestamp': event.message_obj.timestamp,
            'mode': 'add2'  # 标记为模式3，圣诞帽功能
        }
    
        logger.info(f"[梗图] 用户 {user_id} 开始梗图制作流程（模式：add2，圣诞帽）")
        yield event.plain_result("🎅 请发送一张包含人脸的图片，我将为他/她戴上圣诞帽！")

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
            elif mode == 'add1':  # mode == 'add1'
                # 检查模板2是否存在
                if not self.template2_path.exists():
                    logger.error(f"[梗图] 模板2不存在: {self.template2_path}")
                    yield event.plain_result(f"❌ 模板图片不存在\n路径: {self.template2_path}")
                    del waiting_users[user_id]
                    return
                result_image_data = await self.process_image_mode2(image_data)
            else:  # mode == 'add2'
                result_image_data = await self.process_image_mode3(image_data)
            
            
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
        
    async def process_image_mode3(self, user_image_data: bytes) -> bytes:
        """
        模式3：自动识别人脸并戴上圣诞帽！
        新增的 /add2 功能
        
        策略：
        1. 使用 DNN / Anime 级联 / Haar 等多种人脸检测（优先支持较小动漫人脸）
        2. 使用 OpenCV 进行图像处理和叠加圣诞帽
        """
        try:
            logger.info("[圣诞帽]开始处理图片 圣诞老人正在加速赶来")
            
            # 1. 将字节数据转化为 OpenCV 可处理格式
            nparr = np.frombuffer(user_image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("无法解码图片数据")
            
            # 2. 加载圣诞帽图片 (带透明通道)
            hat_path = Path(__file__).parent / "christmas_hat.png"
            if not hat_path.exists():
                raise FileNotFoundError(f"圣诞帽图片未找到, 主人请将圣诞帽图片改名为 `christmas_hat.png` 并放在插件目录下") 
            hat_img = cv2.imread(str(hat_path), cv2.IMREAD_UNCHANGED)
            
            if hat_img is None or hat_img.shape[2] != 4:
                raise ValueError("圣诞帽图片加载失败或不包含 Alpha 通道，请确保为带透明通道的 PNG 图片")

            # 3. 检测人脸（通用方案：DNN 真人优先 + Anime 级联 + Haar + 兜底中心区域）
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2]
            logger.info(f"[圣诞帽] 原始图片尺寸: {w}x{h}")

            faces = []
            models_dir = Path(__file__).parent / "models"

            # 3.1 优先尝试 DNN 真人人脸检测（需要在 models 目录下放好 prototxt 和 caffemodel）
            try:
                prototxt_path = models_dir / "deploy.prototxt"
                caffemodel_path = models_dir / "res10_300x300_ssd_iter_140000.caffemodel"

                if prototxt_path.exists() and caffemodel_path.exists():
                    logger.info(f"[圣诞帽] 使用 DNN 人脸检测: {prototxt_path.name}, {caffemodel_path.name}")
                    net = cv2.dnn.readNetFromCaffe(str(prototxt_path), str(caffemodel_path))

                    blob = cv2.dnn.blobFromImage(
                        cv2.resize(img, (300, 300)),
                        1.0,
                        (300, 300),
                        (104.0, 177.0, 123.0)
                    )
                    net.setInput(blob)
                    detections = net.forward()

                    for i in range(detections.shape[2]):
                        confidence = detections[0, 0, i, 2]
                        if confidence < 0.5:
                            continue
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (x1_d, y1_d, x2_d, y2_d) = box.astype("int")
                        x_d = max(0, x1_d)
                        y_d = max(0, y1_d)
                        w_d = min(w, x2_d) - x_d
                        h_d = min(h, y2_d) - y_d
                        if w_d > 0 and h_d > 0:
                            faces.append((x_d, y_d, w_d, h_d))

                    if faces:
                        logger.info(f"[圣诞帽] DNN 检测到 {len(faces)} 张人脸: {faces}")
                else:
                    logger.info("[圣诞帽] 未找到 DNN 人脸模型文件，跳过 DNN 检测（可在 models 目录下放入 deploy.prototxt 和 res10_300x300_ssd_iter_140000.caffemodel 启用）")
            except Exception as dnn_e:
                logger.error(f"[圣诞帽] DNN 人脸检测失败: {dnn_e}", exc_info=True)

            # 3.2 若 DNN 未检测到，再尝试 Anime 级联检测（适配小尺寸动漫头像）
            if not faces:
                try:
                    anime_cascade_path = models_dir / "lbpcascade_animeface.xml"
                    if anime_cascade_path.exists():
                        logger.info(f"[圣诞帽] 使用 Anime 级联人脸检测: {anime_cascade_path.name}")
                        anime_cascade = cv2.CascadeClassifier(str(anime_cascade_path))
                        if anime_cascade.empty():
                            logger.error(f"[圣诞帽] Anime 级联模型加载失败: {anime_cascade_path}")
                        else:
                            # 针对较小动漫脸，放宽最小尺寸和邻居参数
                            min_face = max(int(min(w, h) * 0.03), 20)
                            faces_anime = anime_cascade.detectMultiScale(
                                gray,
                                scaleFactor=1.1,
                                minNeighbors=3,
                                flags=cv2.CASCADE_SCALE_IMAGE,
                                minSize=(min_face, min_face)
                            )
                            if len(faces_anime) > 0:
                                faces = list(faces_anime)
                                logger.info(f"[圣诞帽] Anime 级联检测到 {len(faces)} 张人脸: {faces}")
                    else:
                        logger.info("[圣诞帽] 未找到 Anime 级联模型 lbpcascade_animeface.xml，可放入 models 目录以增强动漫头像识别效果")
                except Exception as anime_e:
                    logger.error(f"[圣诞帽] Anime 级联人脸检测失败: {anime_e}", exc_info=True)

            # 3.3 如前两种仍未检测到，则回退到 Haar 检测
            if not faces:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                face_cascade = cv2.CascadeClassifier(cascade_path)
                if face_cascade.empty():
                    logger.error(f"OpenCV Haar 人脸检测模型加载失败: {cascade_path}")
                else:
                    logger.info("[圣诞帽] 使用 Haar 人脸检测作为回退方案")
                    # 允许识别较小人脸（约为图像宽/高的 5% 起）
                    min_face_w = max(int(w * 0.05), 24)
                    min_face_h = max(int(h * 0.05), 24)
                    faces_haar = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.1,
                        minNeighbors=3,
                        flags=cv2.CASCADE_SCALE_IMAGE,
                        minSize=(min_face_w, min_face_h)
                    )
                    faces = list(faces_haar) if len(faces_haar) > 0 else []

            # 3.4 如果仍然没有检测到人脸，则兜底：以图片中心区域作为“人脸区域”
            if not faces:
                logger.warn("[圣诞帽] 未检测到人脸，启用兜底方案：使用图片中心区域戴帽子（适配动漫头像/其他生物）")
                fake_w = int(w * 0.5)
                fake_h = int(h * 0.5)
                x_fake = (w - fake_w) // 2
                y_fake = int(h * 0.15)
                faces.append((x_fake, y_fake, fake_w, fake_h))

            logger.info(f"[圣诞帽] 最终用于戴帽子的人脸/区域数量: {len(faces)}，区域列表: {faces}")    
            
            # 5. 为每张人脸添加圣诞帽
            for (x, y, w, h) in faces:
                try:
                    logger.info(f"[圣诞帽] 处理人脸框: x={x}, y={y}, w={w}, h={h}")
                    # 以人脸矩形中心点作为参考（用于左右居中）
                    center_x = x + w // 2
                    # 头顶大致位置 = 人脸框上边再往上偏一点
                    approx_head_top_y = y - int(h * 0.15)

                    # 根据人脸宽度计算帽子缩放比例
                    # 这里稍微放大一些，让帽子看起来更夸张，但限制最大尺寸，避免超过整张图太多
                    base_scale = w / hat_img.shape[1] * 2.0
                    # 将缩放因子限制在一个合理范围
                    hat_scale = max(0.5, min(base_scale, 3.0))

                    hat_width = int(hat_img.shape[1] * hat_scale)
                    hat_height = int(hat_img.shape[0] * hat_scale)

                    # 再次根据整张图尺寸进行裁剪限制
                    max_hat_width = img.shape[1] * 2  # 不超过图像宽度的 2 倍
                    max_hat_height = img.shape[0] * 2  # 不超过图像高度的 2 倍
                    hat_width = min(hat_width, max_hat_width)
                    hat_height = min(hat_height, max_hat_height)

                    if hat_width <= 0 or hat_height <= 0:
                        logger.warn("[圣诞帽] 计算得到的帽子尺寸无效，跳过该人脸")
                        continue

                    resized_hat = cv2.resize(hat_img, (hat_width, hat_height), interpolation=cv2.INTER_AREA)

                    # 计算帽子放置的左上角坐标：
                    # 1. 水平方向以人脸中心对齐
                    # 2. 垂直方向以“头顶附近”为参考，再让帽子略微盖住一点头发
                    head_center_y_for_hat = approx_head_top_y + int(h * 0.05)
                    x1 = center_x - hat_width // 2
                    y1 = head_center_y_for_hat - hat_height // 2
                    x2 = x1 + hat_width
                    y2 = y1 + hat_height

                    # 若完全在图外则跳过
                    if x1 >= img.shape[1] or y1 >= img.shape[0] or x2 <= 0 or y2 <= 0:
                        logger.warn("[圣诞帽] 帽子完全在图像外部，跳过该人脸")
                        continue

                    # 计算实际可见区域
                    overlay_x1 = max(0, -x1) if x1 < 0 else 0
                    overlay_y1 = max(0, -y1) if y1 < 0 else 0
                    overlay_x2 = hat_width - max(0, x2 - img.shape[1])
                    overlay_y2 = hat_height - max(0, y2 - img.shape[0])

                    roi_x1 = max(x1, 0)
                    roi_y1 = max(y1, 0)
                    roi_x2 = min(x2, img.shape[1])
                    roi_y2 = min(y2, img.shape[0])

                    if roi_x1 >= roi_x2 or roi_y1 >= roi_y2:
                        logger.warn("[圣诞帽] 计算得到的 ROI 区域无效，跳过该人脸")
                        continue

                    roi = img[roi_y1:roi_y2, roi_x1:roi_x2]

                    # 提取帽子 RGB 和 Alpha 通道
                    hat_rgb = resized_hat[overlay_y1:overlay_y2, overlay_x1:overlay_x2, :3]
                    alpha_mask = resized_hat[overlay_y1:overlay_y2, overlay_x1:overlay_x2, 3] / 255.0

                    if roi.shape[0] != hat_rgb.shape[0] or roi.shape[1] != hat_rgb.shape[1]:
                        logger.warn(
                            f"[圣诞帽] ROI 与帽子尺寸不匹配，roi={roi.shape}, hat={hat_rgb.shape}，跳过该人脸"
                        )
                        continue

                    # 使用 Alpha 通道进行融合
                    alpha_mask_3 = np.stack([alpha_mask] * 3, axis=-1)
                    roi[:] = roi * (1 - alpha_mask_3) + hat_rgb * alpha_mask_3

                    img[roi_y1:roi_y2, roi_x1:roi_x2] = roi
                except Exception as face_e:
                    logger.error(f"[圣诞帽] 处理单个人脸时出错: {face_e}", exc_info=True)
                    # 出错时仅跳过当前人脸，继续处理其他人脸
                    continue
            
            # 6. 将处理后的 OpenCV 图像转换回字节数据
            is_success, buffer = cv2.imencode(".png", img)
            if not is_success:
                raise ValueError("图片编码失败喵")
            logger.info("[圣诞帽] 图片处理success")    
            return buffer.tobytes()
        
        except Exception as e:
            logger.error(f"[圣诞帽] 处理出错{e}", exc_info=True)     
            raise   
            
            
            