# CuentaMesa

Sistema web de órdenes por mesa y cuenta para restaurantes con servicio en mesas.

Proyecto final de **Diseño de Software** (ITESO), Equipo 05.

## ¿Qué problema resuelve?

Hoy el mesero anota los pedidos en una libreta y el cajero suma los precios con calculadora y teclea el monto en la terminal bancaria. Con CuentaMesa:

- El mesero captura las órdenes desde una tableta.
- El sistema calcula el subtotal, el IVA y el total cada vez que la cuenta cambia.
- El cajero cobra desde una pantalla con la cuenta ya calculada.
- El monto del cobro con tarjeta se envía a la terminal sin teclearlo.
- El ticket se genera a partir de los datos registrados.

## Funcionalidades

### Mesero
| RF | Funcionalidad |
|----|---------------|
| RF-01 | Iniciar sesión con usuario y contraseña |
| RF-02 | Consultar el menú disponible agrupado por categoría |
| RF-03 | Abrir una cuenta para una mesa libre (la mesa pasa a ocupada) |
| RF-04 | Registrar el número de comensales (de 1 a la capacidad de la mesa) |
| RF-05 | Agregar órdenes a una cuenta propia y abierta |
| RF-06 | Agregar productos disponibles a una orden, con cantidad y nota opcional |
| RF-07 | Quitar una línea de producto de una orden |
| RF-08 | Actualizar el estado de un producto (pendiente, en preparación, entregado) |
| RF-09 | Ver el subtotal, el IVA y el total del consumo |
| RF-10 | Solicitar el cobro de la cuenta (pasa a "por cobrar") |

### Cajero
| RF | Funcionalidad |
|----|---------------|
| RF-11 | Aplicar propina como porcentaje o como monto fijo |
| RF-12 | Cobrar en efectivo (con cálculo de cambio) o con tarjeta (límite de 30 s) |
| RF-13 | Cancelar una cuenta indicando un motivo (la mesa queda libre) |
| RF-14 | Ver e imprimir el ticket de una cuenta pagada |
| RF-15 | Crear y editar productos del menú, incluida su disponibilidad |

### Reglas y requisitos destacados
- Los precios del menú incluyen el IVA del 16 %. El sistema calcula el subtotal como `consumo ÷ 1.16` y el IVA como `consumo − subtotal`, así que siempre se cumple que subtotal + IVA = consumo (RN-09, RNF-04).
- Cada mesa tiene a lo más una cuenta abierta (RN-03).
- Solo el mesero que abrió una cuenta puede operarla (RN-06).
- Las contraseñas se guardan con hash y sal, y la sesión expira tras 15 minutos sin actividad (RNF-02).

## Tecnologías

- Python 3.10 o superior
- [Flask](https://flask.palletsprojects.com/) (incluye Werkzeug para el hash de contraseñas y Jinja2 para las plantillas)

## Cómo correrlo

1. Clona el repositorio y entra a la carpeta:
   ```bash
   git clone <url-del-repositorio>
   cd cuentamesa
   ```

2. (Opcional, recomendado) Crea y activa un entorno virtual:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Ejecuta la aplicación:
   ```bash
   python app.py
   ```

5. Abre en el navegador: <http://localhost:5000>

### Usuarios de prueba

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `mesero1` | `1234` | Mesero |
| `mesero2` | `1234` | Mesero |
| `cajero1` | `1234` | Cajero |

Al arrancar, el sistema carga 40 mesas y un menú de ejemplo con 4 categorías. Uno de los productos (Arrachera) está marcado como no disponible para probar RN-02.

### Flujo de prueba sugerido

1. Entra como `mesero1`, abre la mesa 1, crea una orden, agrega productos y pulsa **Solicitar cuenta**.
2. En otra ventana de incógnito, entra como `cajero1` y abre la cuenta desde **Caja**.
3. Aplica una propina y cobra en efectivo o con tarjeta.
4. Revisa el ticket e imprímelo con el botón **Imprimir**.

> **Nota:** la terminal bancaria es **simulada** (`TerminalSimulada` en `terminal.py`): tarda hasta 2 s en responder y aprueba alrededor del 80 % de los cobros. Si rechaza un cobro, la cuenta sigue por cobrar y puedes reintentar o cobrar en efectivo.

> **Importante:** los datos se guardan **en memoria**, así que al detener el servidor se pierden todas las cuentas y los cambios al menú.

## Estructura del proyecto

```
cuentamesa/
├── app.py            # Aplicación Flask: rutas del mesero, del cajero y del menú
├── enums.py          # RolUsuario, EstadoMesa, EstadoCuenta, EstadoDetalleOrden, MetodoPago
├── errores.py        # ReglaNegocioError (violación de una regla de negocio)
├── usuario.py        # Clase Usuario (autenticación y rol)
├── mesa.py           # Clase Mesa (ocupar / liberar)
├── menu.py           # Clases Categoria y Producto
├── cuenta.py         # Clases Cuenta, Orden y DetalleOrden (cálculos y reglas)
├── pago.py           # Clase abstracta Pago y subclases PagoEfectivo / PagoTarjeta
├── terminal.py       # Interfaz ServicioTerminalPago y TerminalSimulada
├── repositorio.py    # Almacenamiento en memoria y datos iniciales
├── plantillas.py     # Plantillas HTML (Jinja2)
└── requirements.txt
```

## Diseño

El código sigue el diseño conceptual de la Entrega 1:

- **Clases:** Usuario, Mesa, Categoria, Producto, Orden, DetalleOrden, Cuenta y Pago.
- **Herencia:** `Pago` es abstracta y tiene dos subclases, `PagoEfectivo` y `PagoTarjeta`. Cada una implementa `procesar_cobro()` a su manera.
- **Composición:** una Cuenta contiene Órdenes, y cada Orden contiene líneas de tipo DetalleOrden.
- **Inversión de dependencias:** `PagoTarjeta` depende de la interfaz `ServicioTerminalPago` y no de una terminal concreta. Así se puede cambiar la terminal simulada por la real sin modificar `PagoTarjeta`.
- **Reglas de negocio:** las reglas se validan dentro de los modelos. Cuando una se viola, el modelo lanza `ReglaNegocioError`, y `app.py` la muestra al usuario como mensaje.

## Pendientes de refactorización

El código tiene comentarios `# REFACTOR:` con mejoras planeadas. Para listarlos:

```bash
grep -rn "REFACTOR" *.py
```

Los principales son:
- Quitar código duplicado: la función `redondear()` y las revisiones de rol repetidas en las rutas.
- Aplicar patrones de diseño:
  - Strategy para la propina.
  - State para los estados de la cuenta.
  - Factory para crear los pagos.
- Cambiar el repositorio en memoria por una base de datos (DEP-02).
- Separar `app.py` en Blueprints y mover el HTML a una carpeta `templates/`.
- Mover a configuración los valores fijos: IVA, límite de 30 s, número máximo de mesas y clave secreta.

## Equipo 05

- Fátima Vélez González
- Karlos Zaid Acosta Dennis
- Sofía Mercado Moreno
- Lilia Alejandra Padilla Hernández