import sys
import os

# garante que os módulos do projeto são encontrados
sys.path.insert(0, os.path.dirname(__file__))

import database as db
from ui.app import App


def main():
    db.inicializar()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
