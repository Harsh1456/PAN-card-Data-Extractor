from ultralytics import YOLO
import cv2

model = YOLO("runs\\obb\\train4\\weights\\best.pt")

image_path = input("Please enter the path to the image: ")

results = model(image_path)

results[0].show()