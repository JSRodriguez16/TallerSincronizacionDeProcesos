import random
import threading
import time


class Jarra:
    def __init__(self, capacidad_inicial: int) -> None:
        self.agua_disponible = capacidad_inicial
        self.lock = threading.Lock()

    def beber(self, cantidad: int, nombre: str) -> None:
        with self.lock:
            if self.agua_disponible >= cantidad:
                print(f"{nombre} esta bebiendo {cantidad} ml.")
                self.agua_disponible -= cantidad
                print(f"Agua restante: {self.agua_disponible} ml\n")
            else:
                print(
                    f"{nombre} quiso beber {cantidad} ml, "
                    f"pero solo quedan {self.agua_disponible} ml.\n"
                )


class Persona(threading.Thread):

    def __init__(self, nombre: str, jarra: Jarra) -> None:
        super().__init__()
        self.nombre = nombre
        self.jarra = jarra

    def run(self) -> None:
        cantidad = random.randint(100, 300)
        time.sleep(random.uniform(0.1, 1.0))
        self.jarra.beber(cantidad, self.nombre)


def main() -> None:
    jarra = Jarra(capacidad_inicial=1000)

    personas = [Persona(f"Persona-{i + 1}", jarra) for i in range(5)]

    for persona in personas:
        persona.start()

    for persona in personas:
        persona.join()

    print(f"Nivel final de agua: {jarra.agua_disponible} ml")


if __name__ == "__main__":
    main()
