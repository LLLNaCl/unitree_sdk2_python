
# 视频流处理模块

import os
import time
import threading
import subprocess
from typing import Dict, Any, Optional, Callable
import psutil

from src.config.config import config
from src.utils.logger import logger

class VideoStreamer:
    """视频流处理类，用于RTSP推流"""
    
    def __init__(self):
        """初始化视频流处理器"""
        self.process = None
        self.running = False
        self.stream_info = {
            "url": config.RTSP_URL,
            "device": config.VIDEO_DEVICE,
            "resolution": config.VIDEO_RESOLUTION,
            "fps": config.VIDEO_FPS,
            "status": "stopped",
            "last_start_time": 0,
            "error_count": 0
        }
        
        # 状态回调函数
        self.status_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # 监控线程
        self.monitor_thread = None
        self.monitor_flag = False
    
    def start(self) -> bool:
        """启动视频流
        
        Returns:
            bool: 是否成功启动
        """
        if self.running:
            logger.info("Video stream is already running")
            return True
            
        try:
            # 停止可能残留的进程
            self._cleanup()
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-f", "v4l2",
                "-i", config.VIDEO_DEVICE,
                "-s", config.VIDEO_RESOLUTION,
                "-r", str(config.VIDEO_FPS),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-tune", "zerolatency",
                "-pix_fmt", "yuv420p",
                "-f", "rtsp",
                "-rtsp_transport", "tcp",
                config.RTSP_URL
            ]
            
            logger.info(f"Starting video stream with command: {' '.join(cmd)}")
            
            # 启动FFmpeg进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 启动输出线程
            self._start_output_threads()
            
            # 更新状态
            self.running = True
            self.stream_info.update({
                "status": "running",
                "last_start_time": time.time(),
                "pid": self.process.pid
            })
            
            # 启动监控线程
            self._start_monitor_thread()
            
            # 调用状态回调
            self._notify_status()
            
            logger.info(f"Video stream started successfully. RTSP URL: {config.RTSP_URL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start video stream: {str(e)}")
            self.stream_info.update({
                "status": "error",
                "error": str(e),
                "error_count": self.stream_info["error_count"] + 1
            })
            self._notify_status()
            return False
    
    def stop(self) -> bool:
        """停止视频流
        
        Returns:
            bool: 是否成功停止
        """
        if not self.running:
            logger.info("Video stream is not running")
            return True
            
        try:
            # 停止监控线程
            self._stop_monitor_thread()
            
            # 终止进程
            if self.process:
                # 尝试优雅终止
                self.process.terminate()
                
                # 等待进程终止
                timeout = 5
                start_time = time.time()
                while self.process.poll() is None and time.time() - start_time < timeout:
                    time.sleep(0.1)
                
                # 如果仍在运行，强制终止
                if self.process.poll() is None:
                    logger.warning("FFmpeg process did not terminate gracefully, killing it")
                    self.process.kill()
            
            # 清理
            self._cleanup()
            
            # 更新状态
            self.running = False
            self.stream_info.update({
                "status": "stopped",
                "pid": None
            })
            
            # 调用状态回调
            self._notify_status()
            
            logger.info("Video stream stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop video stream: {str(e)}")
            return False
    
    def restart(self) -> bool:
        """重启视频流
        
        Returns:
            bool: 是否成功重启
        """
        logger.info("Restarting video stream")
        self.stop()
        time.sleep(1)  # 等待停止完成
        return self.start()
    
    def is_running(self) -> bool:
        """检查视频流是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        return self.running and self.process and self.process.poll() is None
    
    def get_stream_info(self) -> Dict[str, Any]:
        """获取视频流信息
        
        Returns:
            Dict[str, Any]: 视频流信息
        """
        # 更新运行状态
        if self.running and (not self.process or self.process.poll() is not None):
            self.running = False
            self.stream_info.update({
                "status": "stopped",
                "pid": None
            })
        
        return self.stream_info.copy()
    
    def set_status_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """设置状态回调函数
        
        Args:
            callback: 回调函数，参数为流信息
        """
        self.status_callback = callback
    
    def _start_output_threads(self) -> None:
        """启动输出线程处理FFmpeg的 stdout 和 stderr"""
        # 处理stdout
        threading.Thread(
            target=self._process_output,
            args=(self.process.stdout, "stdout"),
            daemon=True
        ).start()
        
        # 处理stderr
        threading.Thread(
            target=self._process_output,
            args=(self.process.stderr, "stderr"),
            daemon=True
        ).start()
    
    def _process_output(self, pipe, pipe_name: str) -> None:
        """处理FFmpeg输出
        
        Args:
            pipe: 输出管道
            pipe_name: 管道名称
        """
        try:
            while True:
                line = pipe.readline()
                if not line:
                    break
                
                line = line.strip()
                if pipe_name == "stderr":
                    # FFmpeg通常在stderr输出信息
                    if "error" in line.lower() or "failed" in line.lower():
                        logger.error(f"FFmpeg error: {line}")
                        self.stream_info.update({
                            "status": "error",
                            "last_error": line,
                            "error_count": self.stream_info["error_count"] + 1
                        })
                        self._notify_status()
                    else:
                        logger.debug(f"FFmpeg output: {line}")
                else:
                    logger.debug(f"FFmpeg stdout: {line}")
        except Exception as e:
            logger.error(f"Error processing FFmpeg {pipe_name}: {str(e)}")
    
    def _start_monitor_thread(self) -> None:
        """启动监控线程"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
            
        self.monitor_flag = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def _stop_monitor_thread(self) -> None:
        """停止监控线程"""
        self.monitor_flag = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join()
    
    def _monitor_loop(self) -> None:
        """监控循环，检查视频流状态并自动重启"""
        while self.monitor_flag:
            try:
                if self.running:
                    # 检查进程是否存活
                    if not self.process or self.process.poll() is not None:
                        logger.warning("Video stream process has died, attempting to restart")
                        self.running = False
                        self.restart()
                
                # 检查运行时间，如果超过24小时则重启
                if self.running and time.time() - self.stream_info["last_start_time"] > 86400:
                    logger.info("Video stream has been running for more than 24 hours, restarting")
                    self.restart()
                
                # 检查CPU和内存使用情况
                if self.process and self.process.poll() is None:
                    try:
                        proc = psutil.Process(self.process.pid)
                        cpu_usage = proc.cpu_percent(interval=1)
                        memory_usage = proc.memory_info().rss / (1024 * 1024)  # MB
                        
                        logger.debug(f"Video stream resource usage - CPU: {cpu_usage}%, Memory: {memory_usage:.2f}MB")
                        
                        # 如果CPU使用率过高，重启
                        if cpu_usage > 95:
                            logger.warning(f"Video stream CPU usage is too high: {cpu_usage}%, restarting")
                            self.restart()
                            
                    except psutil.NoSuchProcess:
                        logger.warning("Video stream process not found, attempting to restart")
                        self.running = False
                        self.restart()
                    except Exception as e:
                        logger.error(f"Error monitoring video stream process: {str(e)}")
            
            except Exception as e:
                logger.error(f"Video stream monitor error: {str(e)}")
            
            # 等待监控间隔
            time.sleep(5)
    
    def _cleanup(self) -> None:
        """清理资源"""
        # 检查是否有残留的FFmpeg进程
        try:
            # 查找所有FFmpeg进程
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'].lower() == 'ffmpeg' or 'ffmpeg' in ' '.join(proc.info['cmdline']).lower():
                    # 检查是否是我们启动的进程
                    if self.process and proc.info['pid'] == self.process.pid:
                        continue
                    
                    # 检查是否正在使用我们的视频设备
                    cmdline = ' '.join(proc.info['cmdline'])
                    if config.VIDEO_DEVICE in cmdline or config.RTSP_URL in cmdline:
                        logger.warning(f"Found existing FFmpeg process using our resources, killing it: {proc.info['pid']}")
                        proc.terminate()
        except Exception as e:
            logger.error(f"Error cleaning up FFmpeg processes: {str(e)}")
    
    def _notify_status(self) -> None:
        """通知状态变化"""
        if self.status_callback:
            try:
                self.status_callback(self.get_stream_info())
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")
