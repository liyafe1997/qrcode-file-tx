import cv2
from pyzbar.pyzbar import decode
import numpy as np
import base64


QRCODE_NUMBER = 24
VIDEO_FILE = "VID.mp4"


current_frame = 0
total_frame = -1
cap = cv2.VideoCapture(VIDEO_FILE)
current_frame_data = {}
all_chunks = {}
Found_All_QR_in_Frame = False
def bytes_with_length_prefix_to_int(b):
    # Convert bytes with length prefix (Which is generated by the func [int_to_bytes_with_length_prefix()]) to int
    length = b[0]
    n_bytes = b[1:1+length]
    n = int.from_bytes(n_bytes, 'big')
    
    return n

# 打开视频文件

def end_of_file():
    #Proces last frame
    for i in range(QRCODE_NUMBER - 1):
        if i not in current_frame_data:
            print(f"Error: Missing QR code {i} for frame {current_frame}")
            exit()
    print(f"------Last frame {frame_index} OK------")
    for key, value in current_frame_data.items():
        if key not in all_chunks:
            all_chunks[key] = value
        else:
            all_chunks[key] += value
            
    final_bytes = bytes()
    for i in range(QRCODE_NUMBER - 1):
        final_bytes += all_chunks[i]
    with open('output.bin', 'wb') as f:
        f.write(final_bytes)
        f.close()
    print("Done")
    cap.release()
    cv2.destroyAllWindows()
    exit()
    pass


while True:
    # Read one video frame from opencv
    ret, frame = cap.read()
    if not ret:
        print("Error: Video reached end but end of file is not found")
        break

    decoded_objects = decode(frame)

    for obj in decoded_objects:
        # Get the bytes data from the QR code
        byte_data = obj.data
        try:
            byte_data = base64.b64decode(byte_data)
        except:
            continue
        if(len(byte_data) < 1):
            continue
        hex_representation = " ".join(f"{byte:02x} " for byte in byte_data)
        if(byte_data == b"EndOfData"):
            print("Found end of file QR code")
            end_of_file()
        qr_count = int(byte_data[0])
        if(int(byte_data[0]) == (QRCODE_NUMBER - 1)):
            frame_index = bytes_with_length_prefix_to_int(byte_data[1:])
            frame_index_len = byte_data[1]
            if (total_frame == -1):
                total_frame = bytes_with_length_prefix_to_int(byte_data[2 + frame_index_len:])
            print(f"Sync QR: Frame index: {frame_index}/{total_frame}")

            if(frame_index > current_frame):
                # New frame detected, check data for last frame
                if (frame_index != current_frame + 1):
                    print(f"Error: Lost frame {current_frame + 1}. Current frame: {frame_index}, last frame: {current_frame}")
                    exit()
                for i in range(QRCODE_NUMBER - 1):
                    if i not in current_frame_data:
                        print(f"Error: Missing QR code {i} for frame {current_frame}")
                        exit()
                print(f"------Frame {current_frame} OK------")
                for key, value in current_frame_data.items():
                    if key not in all_chunks:
                        all_chunks[key] = value
                    else:
                        all_chunks[key] += value
                current_frame_data = {}
                current_frame = frame_index
                Found_All_QR_in_Frame = False
            if(frame_index == total_frame):
                print("Reached the last frame.")

        else:
            if(total_frame == -1):
                continue # Wait for sync QR firstly
            if len(current_frame_data) == QRCODE_NUMBER - 1:
                Found_All_QR_in_Frame = True
                continue # We already got all the QR codes for this frame
            chunk_index = int(byte_data[0])
            chunk_frame = bytes_with_length_prefix_to_int(byte_data[1:])
            if (chunk_frame == current_frame):
                if chunk_index not in current_frame_data:
                    prefix_len = 2 + int(byte_data[1])
                    chunk_data = byte_data[prefix_len:]
                    chunk_data_len = chunk_data[0]
                    chunk_data = chunk_data[1:1+chunk_data_len]

                    if chunk_index == 12 and chunk_frame == 125:
                        pass
                    if chunk_index == 12 and chunk_frame == 126:
                        pass

                    if(len(chunk_data) != chunk_data_len):
                        print(f"Error: Wrong chunk data length: {len(chunk_data)} != {chunk_data_len} in QR code {chunk_index} for frame {current_frame}")
                        exit()
                    current_frame_data[chunk_index] = chunk_data
                    print(f"Adding QR code {chunk_index} for frame:{current_frame}/{total_frame}, QR:{len(current_frame_data)}/{QRCODE_NUMBER - 1}, chunk size: {chunk_data_len}")
            else:
                print(f"Warning: Wrong frame index: {chunk_frame} != {current_frame} in QR code {chunk_index}, ignored!")


        # Draw the bounding box
        pts = obj.polygon
        if len(pts) == 4:  # If found 4 corners of QR code
            pts = np.array(pts, dtype=np.int32)
            pts = pts.reshape((-1, 1, 2))
            color = (0, 0, 255)
            if(Found_All_QR_in_Frame):
                color = (0, 255, 0)
            cv2.polylines(frame, [pts], True, color, 2)


    cv2.imshow('Frame', frame)

    # Press q on keyboard to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()