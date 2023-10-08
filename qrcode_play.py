import sys
import qrcode
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QGridLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
import pickle
import os
from qrcode.image.pil import PilImage
import base64
import multiprocessing
import gzip

QRCODE_NUMBER = 28
QRCODE_SIZE = 5
CHUNK_SIZE = 128
FRAME_RATE = 10
QR_CODE_NUMBER_PER_ROW = 7
FILE_NAME = "test.png"


chunks = []
frames_number = 0
curent_frame = 0


def split_binary_file(file_path, num_splits=QRCODE_NUMBER - 1):
    with open(file_path, 'rb') as file:
        content = file.read()
    
    # Make sure all splits are of equal size, except the last one
    split_size = len(content) // num_splits
    
    splits = []
    start = 0
    
    for i in range(num_splits - 1):
        end = start + split_size
        splits.append(content[start:end])
        start = end
    
    # Put the rest in the last split
    splits.append(content[start:])
    
    return splits

def format_chunk(content, current_split_index):
    formatted_splits = []
    num_full_chunks = len(content) // CHUNK_SIZE
    
    # Split the content into chunks of size CHUNK_SIZE
    for i in range(num_full_chunks):
        print(f"\rGenerating chunk {i}/{num_full_chunks} for QR Code:{current_split_index + 1}/{QRCODE_NUMBER - 1}      ", end="", flush=True)
        chunk_start = i * CHUNK_SIZE
        chunk_end = (i + 1) * CHUNK_SIZE

        formatted_chunk = bytes([current_split_index]) + int_to_bytes_with_length_prefix(i) + bytes([CHUNK_SIZE]) + content[chunk_start:chunk_end]
        formatted_splits.append(generate_qr(formatted_chunk))
        hex_representation = " ".join(f"{byte:02x} " for byte in formatted_chunk)

    # If there are remaining bytes, add them to the last chunk
    remaining_bytes = len(content) % CHUNK_SIZE
    if remaining_bytes > 0:
        print(f"\rGenerating chunk {num_full_chunks}/{num_full_chunks} for QR Code:{current_split_index + 1}/{QRCODE_NUMBER - 1}      ", end="", flush=True)
       
        formatted_chunk = bytes([current_split_index]) + int_to_bytes_with_length_prefix(len(formatted_splits)) + bytes([remaining_bytes]) + content[-remaining_bytes:]
        formatted_splits.append(generate_qr(formatted_chunk))
    
    # Bit field of each chunk QRCode:
    # +----------------------------------+
    # |         Byte 1        | Byte 2    |
    # |                       |           |
    # | Split(QR Code) Index  | Length of |
    # |                       | next      |
    # |                       | integer   |
    # +-----------------------+-----------+
    # | Bytes 3 -> 3+n-1      |           |
    # |                       |           |
    # | Chunk(frame)          |           |
    # | Index Integer         |           |
    # +-----------------------+-----------+
    # | Bytes 3+n ->          |           |
    # |    (variable)         |           |
    # | CHUNK_SIZE            |           |
    # |                       |           |
    # +-----------------------+-----------+
    # | Bytes after CHUNK_SIZE|           |
    # |                       |           |
    # | CHUNK_DATA            |           |
    # |                       |           |
    # |                       |           |
    # +-----------------------+-----------+
    return formatted_splits



def generate_qr(data):
    qr = qrcode.QRCode(
        version=5,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=QRCODE_SIZE,
        border=1,
    )
    base64_data = base64.b64encode(data)
    qr.add_data(base64_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white", image_factory=PilImage).convert('1')
    return img

def int_to_bytes_with_length_prefix(n):
    # Conver a number to bytes with a length prefix
    n_bytes = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    length_byte = len(n_bytes).to_bytes(1, 'big')
    return length_byte + n_bytes


class QRCodeWidget(QWidget):
    def __init__(self):
        super().__init__()


        layout = QGridLayout()
        self.setLayout(layout)
        
        # Create QLabel widgets to display QR codes
        self.labels = [QLabel(self) for _ in range(QRCODE_NUMBER)]
        self.labels[0].setText("Start within 3s. Press any key to exit.")
        self.labels[0].setStyleSheet("color: #000000;")
        for i, label in enumerate(self.labels):
            layout.addWidget(label, i//QR_CODE_NUMBER_PER_ROW, i%QR_CODE_NUMBER_PER_ROW)

        # Set up timer
        self.timerstarter = QTimer(self)
        self.timerstarter.timeout.connect(self.timer_starter_func)
        self.timerstarter.start(3000)

        self.finishedtimer = QTimer(self)
        self.finishedtimer.timeout.connect(self.timer_finished_func)
        self.setStyleSheet("background-color: #FFFFFF;")
        self.setCursor(Qt.BlankCursor)
        self.initUI()
        self.showFullScreen()

    def display_first_frame_func(self):
        self.display_first_frame_timer.stop()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_qrcodes)
        self.timer.start(int(1000 / FRAME_RATE)) 


        
    def timer_starter_func(self):
        self.counter = 0
        self.timerstarter.stop()
        self.update_qrcodes()
        self.display_first_frame_timer = QTimer(self)
        self.display_first_frame_timer.timeout.connect(self.display_first_frame_func)
        # The first frame needs to be displayed longer to prevent frame loss in the video
        self.display_first_frame_timer.start(200) 


    def timer_finished_func(self):
        self.close()
        exit()

    def initUI(self):
        self.setGeometry(100, 100, 800, 320)
        self.setWindowTitle('QR Code File Transmission')
        self.show()

    def update_qrcodes(self):
        global curent_frame

        for i, (chunk, label) in enumerate(zip(chunks, self.labels)):
            img = None
            if curent_frame == -1: # End of File, generate end QR code (All QR Code data = 0xFFFFAA003CFF00FF)
                img = generate_qr(b"EndOfData").convert('RGB')
                qt_img = QImage(img.tobytes(), img.size[0], img.size[1], img.size[1]*3, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                label.setPixmap(pixmap)
            else:
                if(i == (QRCODE_NUMBER - 1)): # last QR code for sync
                    qr_index_bytes = bytes([QRCODE_NUMBER - 1]) 
                    img = generate_qr(qr_index_bytes + int_to_bytes_with_length_prefix(curent_frame)+ int_to_bytes_with_length_prefix(frames_number)).convert('RGB')
                else: # data QR codes
                    img = chunk[curent_frame].convert('RGB')

                qt_img = QImage(img.tobytes(), img.size[0], img.size[1], img.size[1]*3, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                label.setPixmap(pixmap)

        if(curent_frame == -1):
            self.timer.stop()
            print("Finished!")
            self.finishedtimer.start(1000)
            return
        print(f"Frame: {curent_frame}/{frames_number}")
        curent_frame += 1
        if(curent_frame > frames_number):
            curent_frame = -1

        self.counter += 1

    def keyPressEvent(self, event):
        # Press any key to exit
        exit()

def all_elements_equal(lst):
    return all(x == lst[0] for x in lst)


def qr_mp_wrapper(args):
    # 包装函数，返回(索引, 结果)
    i, data = args
    return i, format_chunk(data, i)


def generate_qr_concurrently(split_data):
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    
    results = pool.map(qr_mp_wrapper, enumerate(split_data))

    pool.close()
    pool.join()
    
    sorted_results = sorted(results, key=lambda x: x[0])

    for i, result in sorted_results:
        chunks[i] = result
    frames_count = [len(res[1]) for res in sorted_results]
    return frames_count

def main():
    global frames_number
    global chunks
    loaded_data = None
    Cahce_available = True
    if os.path.exists('qr_cache.pickle'):
        # Load QR code cache
        with gzip.open('qr_cache.pickle', 'rb') as f:
            print("Loading QR codes from qr_cache.pickle...")
            loaded_data = pickle.load(f)
        try:
            if(loaded_data["QRCODE_NUMBER"] != QRCODE_NUMBER or loaded_data["CHUNK_SIZE"] != CHUNK_SIZE or loaded_data["QRCODE_SIZE"] != QRCODE_SIZE):
                print("QR code parameters changed. Regenerate QR codes!")
                Cahce_available = False
        except:
            print("Load QR code cache failed. Regenerate QR codes!")
            Cahce_available = False
    else:
        print("qr_cache.pickle not found. Generate QR codes first!")
        Cahce_available = False

    if Cahce_available == False:
        split_data = split_binary_file(FILE_NAME)
        frames_count = []
        for i in range (len(split_data)):
            chunks.append([])

        chunks.append(0) # The last one for the last QR code for sync, it will be generated during playing
        print("Generating QR codes by multiprocessing ...\n\n")
        frames_count = generate_qr_concurrently(split_data)
        print(f"\n\nGroups of QR codes for data: {len(frames_count)}")
        if(all_elements_equal(frames_count)):
            print(f"All QR codes have the same number of frames:{frames_count[0]}. Good!")
            frames_number = frames_count[0] - 1
        else:
            print("QR codes have different number of frames. Exit!")
            exit()
        print("Saving QR codes to cache...")
        saving_dict = {}
        saving_dict["frames_number"] = frames_number
        saving_dict["chunks"] = chunks
        saving_dict["QRCODE_NUMBER"] = QRCODE_NUMBER
        saving_dict["CHUNK_SIZE"] = CHUNK_SIZE
        saving_dict["QRCODE_SIZE"] = QRCODE_SIZE
        with gzip.open('qr_cache.pickle', 'wb') as f:
            pickle.dump(saving_dict, f)
            f.close()
    else:
        frames_number = loaded_data["frames_number"]
        chunks = loaded_data["chunks"]
        del loaded_data
        print("QR codes loaded from cache.")
    
    # Saving data

    app = QApplication(sys.argv)
    _ = QRCodeWidget()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()