# Permite importar servidor_rrhh y agente desde la carpeta de pruebas.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
