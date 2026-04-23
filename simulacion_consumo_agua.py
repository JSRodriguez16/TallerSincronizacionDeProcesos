import random
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Tuple
from queue import Queue


class Jarra:

    def __init__(self, capacidad_inicial: int, max_bebedores: int = 2) -> None:
        self.agua_disponible = capacidad_inicial
        self.capacidad_total = capacidad_inicial

        self.mutex = threading.Lock()

        self.monitor = threading.Condition(self.mutex)

        self.semaforo = threading.Semaphore(max_bebedores)

        self.callback_actualizar = None
        self.eventos = Queue()
        self.ultimo_relleno = 0
        self.corriendo = True

    def set_callback(self, callback: Callable) -> None:
        self.callback_actualizar = callback

    def beber(self, cantidad: int, nombre: str) -> bool:
        self.semaforo.acquire()

        try:
            with self.monitor:
                max_intentos = 5
                intento = 0

                while self.agua_disponible < cantidad and intento < max_intentos:
                    evento = f"{nombre} esta esperando ({cantidad} ml, intento {intento + 1}/{max_intentos})"
                    print(evento)
                    self.eventos.put(("espera", nombre, self.agua_disponible))

                    self.monitor.wait(timeout=5)
                    intento += 1

                if self.agua_disponible >= cantidad:
                    print(f"{nombre} esta bebiendo {cantidad} ml.")
                    self.agua_disponible -= cantidad

                    evento = f"{nombre} bebio {cantidad} ml. Quedan: {self.agua_disponible} ml"
                    print(evento)
                    self.eventos.put(("bebida", nombre, self.agua_disponible))

                    self.monitor.notify_all()
                    return True
                else:
                    evento = f"{nombre} no siguio esperando (insuficiente agua: {self.agua_disponible} ml)"
                    print(evento)
                    self.eventos.put(("error", nombre, self.agua_disponible))
                    return False
        finally:
            self.semaforo.release()

    def rellenar(self, cantidad: int, nombre: str = "Sistema") -> None:
        with self.monitor:
            anterior = self.agua_disponible
            self.agua_disponible = min(
                self.agua_disponible + cantidad, self.capacidad_total
            )

            if anterior != self.agua_disponible:
                self.ultimo_relleno = time.time()
                evento = f"{nombre} relleno la jarra: {anterior} + {cantidad} = {self.agua_disponible} ml"
                print(evento)
                self.eventos.put(("relleno", nombre, self.agua_disponible))

    def get_evento(self) -> Tuple[str, str, int]:
        try:
            return self.eventos.get_nowait()
        except:
            return None


class Persona(threading.Thread):
    def __init__(self, nombre: str, jarra: Jarra, num_intentos: int = 1) -> None:
        super().__init__(daemon=False)
        self.nombre = nombre
        self.jarra = jarra
        self.num_intentos = num_intentos

    def run(self) -> None:
        intento = 0
        while self.jarra.corriendo and intento < self.num_intentos:
            cantidad = random.randint(10, 50)
            time.sleep(random.uniform(0.3, 1.0))
            self.jarra.beber(cantidad, self.nombre)
            time.sleep(1)
            intento += 1


class SimulacionGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Sincronizacion: Simulacion de Consumo de Agua")
        self.root.geometry("800x720")
        self.root.resizable(False, False)

        self.jarra = None
        self.personas: List[Persona] = []
        self.corriendo = False
        self.thread_relleno = None
        self.detener_relleno = False
        self.ultimo_relleno_manual = 0

        self._crear_interfaz()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _crear_interfaz(self) -> None:
        # Frame de autor
        frame_autor = ttk.Frame(self.root, padding="5")
        frame_autor.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(
            frame_autor, 
            text="Autor: Juan Sebastian Rodriguez Carreño", 
            font=("Arial", 9, "italic"),
            foreground="gray"
        ).pack(side=tk.LEFT)

        frame_control = ttk.Frame(self.root, padding="10")
        frame_control.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(
            frame_control, text="Capacidad inicial (ml):", font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)
        self.spinbox_capacidad = ttk.Spinbox(
            frame_control, from_=500, to=5000, increment=100, width=10
        )
        self.spinbox_capacidad.set(1000)
        self.spinbox_capacidad.pack(side=tk.LEFT, padx=5)

        ttk.Label(frame_control, text="Numero de personas:", font=("Arial", 10)).pack(
            side=tk.LEFT, padx=5
        )
        self.spinbox_personas = ttk.Spinbox(
            frame_control, from_=1, to=10, increment=1, width=10
        )
        self.spinbox_personas.set(5)
        self.spinbox_personas.pack(side=tk.LEFT, padx=5)

        ttk.Label(
            frame_control, text="Max bebedores (semaforo):", font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)
        self.spinbox_semaforo = ttk.Spinbox(
            frame_control, from_=1, to=5, increment=1, width=10
        )
        self.spinbox_semaforo.set(2)
        self.spinbox_semaforo.pack(side=tk.LEFT, padx=5)

        frame_botones = ttk.Frame(self.root, padding="10")
        frame_botones.pack(fill=tk.X, padx=10, pady=5)

        self.btn_iniciar = ttk.Button(
            frame_botones, text="Iniciar Simulacion", command=self._iniciar_simulacion
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=5)

        self.btn_detener = ttk.Button(
            frame_botones,
            text="Detener simulacion",
            command=self._detener_simulacion,
            state=tk.DISABLED,
        )
        self.btn_detener.pack(side=tk.LEFT, padx=5)

        self.btn_rellenar = ttk.Button(
            frame_botones,
            text="Rellenar Jarra",
            command=self._rellenar_jarra,
            state=tk.DISABLED,
        )
        self.btn_rellenar.pack(side=tk.LEFT, padx=5)

        frame_jarra = ttk.LabelFrame(self.root, text="Estado de la Jarra", padding="10")
        frame_jarra.pack(fill=tk.X, padx=10, pady=10)

        self.canvas_agua = tk.Canvas(
            frame_jarra, width=600, height=100, bg="white", relief=tk.SUNKEN
        )
        self.canvas_agua.pack(pady=5)

        frame_datos = ttk.Frame(frame_jarra)
        frame_datos.pack(fill=tk.X)

        self.label_agua = ttk.Label(
            frame_datos, text="Agua disponible: 0 ml", font=("Arial", 11, "bold")
        )
        self.label_agua.pack(side=tk.LEFT, padx=10)

        self.label_porcentaje = ttk.Label(
            frame_datos,
            text="Porcentaje: 0%",
            font=("Arial", 11, "bold"),
            foreground="blue",
        )
        self.label_porcentaje.pack(side=tk.LEFT, padx=10)

        frame_log = ttk.LabelFrame(self.root, text="Registro de Eventos", padding="10")
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(frame_log)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_log = tk.Text(
            frame_log,
            height=15,
            width=95,
            yscrollcommand=scrollbar.set,
            font=("Courier", 9),
            state=tk.DISABLED,
        )
        self.text_log.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_log.yview)

        self.label_info = ttk.Label(
            self.root, text="Listo para iniciar", font=("Arial", 9)
        )
        self.label_info.pack(pady=5)

    def _dibujar_jarra(self, agua_actual: int, capacidad: int) -> None:
        self.canvas_agua.delete("all")

        x1, y1, x2, y2 = 50, 20, 550, 80
        self.canvas_agua.create_rectangle(x1, y1, x2, y2, outline="black", width=2)

        if capacidad > 0:
            altura_agua = (agua_actual / capacidad) * (y2 - y1)
            self.canvas_agua.create_rectangle(
                x1 + 2, y2 - altura_agua, x2 - 2, y2 - 2, fill="#3498db", outline=""
            )

        self.canvas_agua.create_text(
            300,
            50,
            text=f"Agua: {agua_actual} ml",
            font=("Arial", 12, "bold"),
            fill="black",
        )

    def _agregar_evento(self, tipo: str, persona: str, agua: int) -> None:
        timestamp = time.strftime("%H:%M:%S")
        mensaje = f"[{timestamp}] {persona}: {agua} ml\n"

        self.text_log.config(state=tk.NORMAL)
        self.text_log.insert(tk.END, mensaje)
        self.text_log.see(tk.END)
        self.text_log.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def _actualizar_gui(self) -> None:
        if not self.corriendo or self.jarra is None:
            return

        evento = self.jarra.get_evento()
        while evento:
            tipo, persona, agua = evento
            self._agregar_evento(tipo, persona, agua)
            evento = self.jarra.get_evento()

        agua_actual = self.jarra.agua_disponible
        capacidad = self.jarra.capacidad_total

        self._dibujar_jarra(agua_actual, capacidad)
        self.label_agua.config(text=f"Agua disponible: {agua_actual} ml")

        porcentaje = (agua_actual / capacidad * 100) if capacidad > 0 else 0
        self.label_porcentaje.config(text=f"Porcentaje: {porcentaje:.1f}%")

        if self.corriendo:
            self.root.after(100, self._actualizar_gui)

    def _iniciar_simulacion(self) -> None:
        if self.corriendo:
            return

        self.corriendo = True
        self.btn_iniciar.config(state=tk.DISABLED)
        self.btn_detener.config(state=tk.NORMAL)
        self.btn_rellenar.config(state=tk.NORMAL)
        self.spinbox_capacidad.config(state=tk.DISABLED)
        self.spinbox_personas.config(state=tk.DISABLED)
        self.spinbox_semaforo.config(state=tk.DISABLED)

        self.text_log.config(state=tk.NORMAL)
        self.text_log.delete("1.0", tk.END)
        self.text_log.config(state=tk.DISABLED)

        capacidad = int(self.spinbox_capacidad.get())
        num_personas = int(self.spinbox_personas.get())
        max_bebedores = int(self.spinbox_semaforo.get())

        self.jarra = Jarra(capacidad_inicial=capacidad, max_bebedores=max_bebedores)

        self.personas = [
            Persona(
                f"Persona-{i + 1}", self.jarra, num_intentos=50
            )  # 50 intentos = mas actividad
            for i in range(num_personas)
        ]

        for persona in self.personas:
            persona.start()

        self.label_info.config(
            text=f"Simulacion en ejecucion: {num_personas} personas, semaforo={max_bebedores}"
        )

        self.root.after(100, self._actualizar_gui)

    def _detener_simulacion(self) -> None:
        self.corriendo = False
        if self.jarra:
            self.jarra.corriendo = False
        self.detener_relleno = True
        self.btn_iniciar.config(state=tk.NORMAL)
        self.btn_detener.config(state=tk.DISABLED)
        self.btn_rellenar.config(state=tk.DISABLED)
        self.spinbox_capacidad.config(state=tk.NORMAL)
        self.spinbox_personas.config(state=tk.NORMAL)
        self.spinbox_semaforo.config(state=tk.NORMAL)

        self.label_info.config(text="Simulacion detenida")

    def _rellenar_jarra(self) -> None:
        if self.jarra:
            ahora = time.time()
            if ahora - self.ultimo_relleno_manual >= 2.0:
                self.jarra.rellenar(self.jarra.capacidad_total, "Usuario")
                self.ultimo_relleno_manual = ahora

    def _relleno_automatico_thread(self) -> None:
        while self.corriendo and not self.detener_relleno:
            if self.jarra:
                agua_actual = self.jarra.agua_disponible
                capacidad = self.jarra.capacidad_total

                if agua_actual < capacidad * 0.25:
                    self.jarra.rellenar(capacidad // 2, "Sistema (Auto)")

            time.sleep(0.5)

    def _on_closing(self) -> None:
        self.corriendo = False
        self.detener_relleno = True
        if self.jarra:
            self.jarra.corriendo = False

        for persona in self.personas:
            persona.join(timeout=1)

        self.root.destroy()

    def ejecutar(self) -> None:
        self.root.mainloop()


def main_cli() -> None:
    print("=" * 60)
    print("Simulacion de Consumo de Agua - Version CLI")
    print("=" * 60)

    jarra = Jarra(capacidad_inicial=1000, max_bebedores=2)

    personas = [Persona(f"Persona-{i + 1}", jarra, num_intentos=50) for i in range(5)]

    for persona in personas:
        persona.start()

    for persona in personas:
        persona.join()

    print(f"\n{'=' * 60}")
    print(f"Nivel final de agua: {jarra.agua_disponible} ml")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SimulacionGUI(root)
    app.ejecutar()
