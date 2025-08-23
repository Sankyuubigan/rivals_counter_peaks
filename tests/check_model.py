import onnx
import numpy as np
# Проверяем модель model_q4.onnx
model_path = "vision_models/dinov2-base/model_q4.onnx"
try:
    # Загружаем модель
    model = onnx.load(model_path)
    
    # Проверяем все операции в модели
    ops = set()
    for node in model.graph.node:
        ops.add(node.op_type)
    
    print(f"Анализ модели: {model_path}")
    print("=" * 50)
    print("Операции в модели:")
    for op in sorted(ops):
        print(f" - {op}")
    
    # Проверяем наличие кастомных операций Microsoft
    custom_ops = [op for op in ops if "MatMul" in op or "Bits" in op or "NBits" in op]
    print(f"\nКастомные операции Microsoft:")
    if custom_ops:
        for op in custom_ops:
            print(f" - {op}")
    else:
        print("Не найдено")
    
    # Если есть MatMulNBits, выведем информацию о нём
    if "MatMulNBits" in ops:
        print("\nИнформация об операциях MatMulNBits:")
        for node in model.graph.node:
            if node.op_type == "MatMulNBits":
                print(f" - Имя: {node.name}")
                print(f" - Входы: {[inp.name for inp in node.input]}")
                print(f" - Выходы: {[out.name for out in node.output]}")
                print(f" - Количество входов: {len(node.input)}")
    
    # Проверяем входы и выходы модели
    print("\nВходы модели:")
    for input in model.graph.input:
        print(f" - {input.name}: {input.type.tensor_type.shape.dim}")
    
    print("\nВыходы модели:")
    for output in model.graph.output:
        print(f" - {output.name}: {output.type.tensor_type.shape.dim}")
    
except Exception as e:
    print(f"Ошибка при загрузке модели: {e}")
print("\n" + "=" * 50)
print("Проверка наличия файла модели...")
import os
if os.path.exists(model_path):
    print(f"Файл существует: {model_path}")
    print(f"Размер файла: {os.path.getsize(model_path) / (1024*1024):.2f} МБ")
else:
    print(f"Файл НЕ существует: {model_path}")
print(f"\nФайлы в папке vision_models/dinov2-base/:")
if os.path.exists("vision_models/dinov2-base/"):
    for file in os.listdir("vision_models/dinov2-base/"):
        filepath = os.path.join("vision_models/dinov2-base/", file)
        print(f" - {file} ({os.path.getsize(filepath) / (1024*1024):.2f} МБ)")
else:
    print("Папка vision_models/dinov2-base/ не существует!")