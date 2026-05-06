import cv2
import os

def extract_frames_per_second(video_path, output_dir, frames_per_second=3):
    """
    按固定时间间隔提取帧（每秒提取 frames_per_second 张图片）
    
    Args:
        video_path: 输入视频文件路径
        output_dir: 输出文件夹路径
        frames_per_second: 每秒要提取的帧数（默认 3）
    """
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"错误：无法打开视频文件 '{video_path}'")
        return

    # 获取视频的帧率 (FPS)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        print("错误：无法获取视频帧率")
        cap.release()
        return

    # 计算帧间隔（每隔多少帧提取一帧）
    # 例如：fps=30，要每秒3帧，则每10帧提取一帧
    frame_interval = int(round(fps / frames_per_second))
    if frame_interval < 1:
        frame_interval = 1

    print(f"视频帧率: {fps:.2f} fps")
    print(f"目标: 每秒提取 {frames_per_second} 帧")
    print(f"实际帧间隔: {frame_interval} 帧/张")
    print(f"输出目录: {output_dir}")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 每隔 frame_interval 帧保存一张
        if frame_count % frame_interval == 0:
            # 命名规则：frame_0001.jpg, frame_0002.jpg ...
            filename = os.path.join(output_dir, f"frame_{saved_count+1:06d}.jpg")
            cv2.imwrite(filename, frame)
            saved_count += 1

        frame_count += 1

        # 可选：显示进度（每1000帧打印一次）
        if frame_count % 1000 == 0:
            print(f"已处理 {frame_count} 帧，已保存 {saved_count} 张图片")

    cap.release()
    print(f"处理完成！")
    print(f"总帧数: {frame_count}")
    print(f"共保存 {saved_count} 张图片到: {output_dir}")

if __name__ == "__main__":
    # 示例用法：将 'input.avi' 中的帧每秒提取3张，保存到 'output_frames' 文件夹
    extract_frames_per_second(r"C:\Users\admin\Desktop\label\origin\0430\LHR04_A004_2026_04_30_10_17_40_lfhs.avi", 
                              r"output/", frames_per_second=3)