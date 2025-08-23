import onnx
import numpy as np

# Проверяем модель model_q4.onnx
model_path = "vision_models/dinov2-base/model_q4.onnx"

try:
    # Загружаем модель
    model = onnx.load(model_path)
    
    # Проверяем все операции в модели
    ops = set()
    matmul_ops = []
    
    for node in model.graph.node:
        ops.add(node.op_type)
        if "MatMul" in node.op_type:
            matmul_ops.append({
                "name": node.name,
                "op_type": node.op_type,
                "inputs": len(node.input),
                "outputs": len(node.output),
                "input_names": node.input,
                "output_names": node.output
            })
    
    print(f"Анализ модели: {model_path}")
    print("=" * 50)
    print(f"Всего операций в модели: {len(ops)}")
    print("Операции в модели:")
    for op in sorted(ops):
        print(f" - {op}")
    
    print("\nОперации MatMul:")
    for op in matmul_ops:
        print(f" - Имя: {op['name']}")
        print(f"   Тип: {op['op_type']}")
        print(f"   Входов: {op['inputs']}")
        print(f"   Выходов: {op['outputs']}")
        print(f"   Входы: {op['input_names']}")
        print(f"   Выходы: {op['output_names']}")
        print()
    
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