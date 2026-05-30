# src/codegen/stack_frame.py

from typing import Dict, List, Optional
from src.ir.ir_instructions import FunctionIR

class StackFrameManager:
    def __init__(self, func: FunctionIR):
        self.func = func
        # Слоты для временных переменных (включая те, что сопоставлены локальным переменным)
        self.temp_offsets: Dict[int, int] = {}
        self.total_size: int = 0

    def allocate(self):
        # Назначаем слоты для всех временных от 1 до temp_counter
        offset = -8
        for i in range(1, self.func.temp_counter + 1):
            self.temp_offsets[i] = offset
            offset -= 8

        # Общий размер (положительное число)
        self.total_size = -offset if offset < 0 else 0
        # Выравнивание до 16 байт
        if self.total_size % 16 != 0:
            self.total_size += 16 - (self.total_size % 16)

    def get_temp_offset(self, temp_index: int) -> int:
        return self.temp_offsets[temp_index]