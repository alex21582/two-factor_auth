from face_recognition import load_image_file, face_encodings, face_locations, face_distance, compare_faces
import cv2
import numpy as np
from pathlib import Path


def get_face_encodings(dir_path: Path) -> (list, list):
    encoding_lst, name_lst = list(), list()
    dir = Path(dir_path)
    for entry in dir.iterdir():
        if entry.suffix == '.jpg':
            name_lst.append(entry.name.split('.')[0])
            face_image = load_image_file(entry)
            face_encoding = face_encodings(face_image)[0]
            encoding_lst.append(face_encoding)
    return name_lst, encoding_lst


def prepare_frame(frame):
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])
    return rgb_small_frame


def face_recognise(face_encodings_lst: list, known_face_encodings: list, known_face_names: list) -> list:
    face_names_lst = list()
    for face_encoding_ in face_encodings_lst:
        matches = compare_faces(known_face_encodings, face_encoding_)
        name = "Unknown"
        face_distances = face_distance(known_face_encodings, face_encoding_)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
        face_names_lst.append(name)
    return face_names_lst
