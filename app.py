from utils.face_functions import *
from utils.mac_functions import *
import logging
import time

# Глобальные переменные
FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]
DIR_PATH = ROOT.joinpath("images")  # Путь к файлам с изображениями
INIT_FILE_NAME = ROOT.joinpath('init_macs.txt')  # Файл с начальными МАС-адресами
PERIOD_SEC = 30  # Время сканирования МАС-адресов в период идентификации в сек
INIT_PERIOD_SEC = 30  # Время сканирования МАС-адресов в режиме анализа внешних устройств в сек
font = cv2.FONT_HERSHEY_DUPLEX
def_mac = MacObj('-999', 'Not detected')

# Настройка логирования
logger = logging.getLogger('__name__')
logger.setLevel(logging.DEBUG)
f_handler = logging.FileHandler(filename=ROOT.joinpath("app.log"), mode='w')
formatter = logging.Formatter('%(asctime)s: %(filename)s - %(levelname)s - %(message)s')
f_handler.setFormatter(formatter)
logger.addHandler(f_handler)

# Получение эмбедингов и имен для имеющихся в базе сотрудников
known_face_names, known_face_encodings = get_face_encodings(DIR_PATH)


def main():
    logger.debug(f"Start program.")
    video_capture = cv2.VideoCapture(0)
    process_this_frame = True

    # Проверка наличия файла с МАС-адресами внешних устройств
    if not find_init_file(INIT_FILE_NAME):
        logger.debug(f"Init file wasn't found. Creating new file: {INIT_FILE_NAME}.")
        print("Init file not found. Creating...")

        port = get_serial_port()  # Сканирование и открытие СОМ-порта
        mac_flow = serial.Serial(port, 115200)

        logger.debug(f"Open serial port for creating init_file: {port}.")
        print(f"Open serial port for creating init_file: {port}.")

        init_macs_set = create_init_macs_set(INIT_PERIOD_SEC, mac_flow)  # Получение МАС-адресов внешних устройств
        write_init_file(init_macs_set, INIT_FILE_NAME)  # Запись МАС-адресов внешних устройств в init файл

    # Если файл существует, читаем его и начинаем сканирование
    init_macs_set = read_init_file(INIT_FILE_NAME)

    logger.debug(f"Init file was found: {INIT_FILE_NAME}. {len(init_macs_set)} macs were found.")
    print(f"Init file was found: {INIT_FILE_NAME}. {len(init_macs_set)} macs were found.")

    port = get_serial_port()

    logger.debug(f"Open serial port for scanning: {port}.")
    print(f"Open serial port for scanning: {port}.")

    mac_flow = serial.Serial(port, 115200)
    cv2.namedWindow("Result", cv2.WINDOW_AUTOSIZE)

    while True:
        ret, frame = video_capture.read()
        if process_this_frame and ret:
            rgb_small_frame = prepare_frame(frame)  # Обработка фрейма для дальнейшего использования
            face_locations_lst = face_locations(rgb_small_frame)
            # Если лицо в кадре обнаружено, то начинаем распознавание
            if len(face_locations_lst) > 0:
                found_macs = {def_mac}  # Создаем множества для хранения найденных МАС-адресов
                face_encodings_lst = face_encodings(rgb_small_frame, face_locations_lst)  # Расчет эмбедингов для
                # обнаруженного лица
                face_names_lst = face_recognise(face_encodings_lst,  # Ищем соответствие в базе
                                                known_face_encodings,
                                                known_face_names)
                # Начинаем поиск МАС-адресов
                start_time = int(time.time())
                while (int(time.time()) - start_time) < PERIOD_SEC:
                    rssi_obj, mac_obj = read_macs(mac_flow)  # Чтение данных из СОМ-порта
                    if None not in [mac_obj, rssi_obj]:
                        mac, rssi = mac_obj.string, rssi_obj.string
                        if mac not in init_macs_set:  # Если полученный МАС-адрес не содержится в init-файле,
                            # добавляем его в хранилище
                            found_macs.add(MacObj(rssi, mac))

                logger.debug(f"All found macs: {tuple((obj.rssi, obj.mac) for obj in found_macs)}")
                print(f"All found macs: {tuple((obj.rssi, obj.mac) for obj in found_macs)}")

                highest_rssi = sorted(found_macs, key=lambda x: x.rssi)[0]
                current_mac = highest_rssi.mac  # Выбираем из найденных адресов МАС-адрес с наибольшим rssi

                logger.debug(f"Current mac: {current_mac}. Person: {face_names_lst[0]}")
                print(f"Current mac: {current_mac}. Person: {face_names_lst[0]}")

                # Отображение результатов
                for (top, right, bottom, left), name, mac_i in zip(face_locations_lst,
                                                                   face_names_lst,
                                                                   [current_mac] * len(face_names_lst)):

                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4

                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                    cv2.rectangle(frame, (left, top - 35), (right, top), (0, 0, 255), cv2.FILLED)
                    cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
                    cv2.putText(frame, mac_i, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)
                    cv2.imshow("Result", frame)
                    process_this_frame = not process_this_frame
        # Отслеживаем закрытие окна
        if cv2.getWindowProperty('Result', cv2.WND_PROP_VISIBLE) < 1:
            process_this_frame = not process_this_frame

        # Видеопоток
        cv2.imshow('Video', frame)

        # Нажмите 'q' для выхода
        if cv2.waitKey(1) & 0xFF == ord('q'):
            mac_flow.close()
            break

    # Обработчик окна камеры
    video_capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
