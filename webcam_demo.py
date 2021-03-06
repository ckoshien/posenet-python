import tensorflow as tf
import cv2
import time
import argparse

import posenet

parser = argparse.ArgumentParser()
parser.add_argument('--model', type=int, default=101)
parser.add_argument('--cam_id', type=int, default=0)
parser.add_argument('--cam_width', type=int, default=1280)
parser.add_argument('--cam_height', type=int, default=720)
parser.add_argument('--scale_factor', type=float, default=0.7125)
parser.add_argument('--output_stride', type=float, default=8)
parser.add_argument('--file', type=str, default=None, help="Optionally use a video file instead of a live camera")
args = parser.parse_args()

outputFile="output.mp4"
video = cv2.VideoCapture(args.file)
outFourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
W = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
out = cv2.VideoWriter(outputFile, outFourcc, 30.0,
                          (W, H))  # 出力先のファイルを開く


def main():
    with tf.Session() as sess:
        model_cfg, model_outputs = posenet.load_model(args.model, sess)
        output_stride = model_cfg['output_stride']
        #print(model_cfg)

        if args.file is not None:
            cap = cv2.VideoCapture(args.file)
        else:
            cap = cv2.VideoCapture(args.cam_id)
        cap.set(3, args.cam_width)
        cap.set(4, args.cam_height)

        start = time.time()
        frame_count = 0
        while True:
            try:
                input_image, display_image, output_scale = posenet.read_cap(
                cap, scale_factor=args.scale_factor, output_stride=output_stride)

                heatmaps_result, offsets_result, displacement_fwd_result, displacement_bwd_result = sess.run(
                    model_outputs,
                    feed_dict={'image:0': input_image}
                )

                pose_scores, keypoint_scores, keypoint_coords = posenet.decode_multi.decode_multiple_poses(
                    heatmaps_result.squeeze(axis=0),
                    offsets_result.squeeze(axis=0),
                    displacement_fwd_result.squeeze(axis=0),
                    displacement_bwd_result.squeeze(axis=0),
                    output_stride=output_stride,
                    max_pose_detections=10,
                    min_pose_score=0.15)

                keypoint_coords *= output_scale
                

                # TODO this isn't particularly fast, use GL for drawing and display someday...
                overlay_image = posenet.draw_skel_and_kp(
                    display_image, pose_scores, keypoint_scores, keypoint_coords,
                    min_pose_score=0.15, min_part_score=0.1)
                overlay_image = cv2.rectangle(
                    overlay_image,
                    (
                        775,
                        int((keypoint_coords[0,5,0]/2 + keypoint_coords[0,11,0]/2))
                    ),
                    (
                        825,
                        int(keypoint_coords[0,14,0])
                    ),
                    (255,255,255),5
                )

                cv2.imshow('posenet', overlay_image)
                frame_count += 1
                out.write(overlay_image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except IOError as e:
                #終了処理
                out.write(overlay_image)
                out.release()
                video.release()
                break

            
        print('Average FPS: ', frame_count / (time.time() - start))
        out.release()
        video.release()

if __name__ == "__main__":
    main()