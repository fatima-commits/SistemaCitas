"""GeneradorTicket (H-05): da formato al ticket de una cuenta pagada (RF-14, RN-14)."""
from decimal import Decimal

from Errores import ReglaNegocioError
from Cuenta import TASA_IVA

class GeneradorTicket:
    def generar(self, resumen, pagos):
        """RF-14, RN-14: solo si hay al menos un pago registrado."""
        if not pagos or any(p.id_pago is None for p in pagos):
            raise ReglaNegocioError("La cuenta no tiene un pago registrado (RN-14).")
        lineas = [
            "CUENTAMESA",
            f"Folio cuenta: {resumen.folio}   Mesa: {resumen.numero_mesa}",
            f"Mesero: {resumen.nombre_mesero}   Comensales: {resumen.numero_comensales}",
            f"Fecha: {pagos[0].fecha_hora:%d/%m/%Y %H:%M}",
            "-" * 40,
        ]
        for cantidad, nombre, importe in resumen.lineas:
            lineas.append(f"{cantidad:>3} x {nombre[:22]:<22} {importe:>10.2f}")
        total = sum((p.monto for p in pagos), Decimal("0.00"))
        lineas += [
            "-" * 40,
            f"{'Subtotal':<28}{resumen.subtotal:>12.2f}",
            f"{f'IVA {TASA_IVA * 100:.0f}%':<28}{resumen.iva:>12.2f}",
            f"{'Consumo':<28}{resumen.consumo:>12.2f}",
            f"{'Propina':<28}{resumen.propina:>12.2f}",
            f"{'TOTAL':<28}{total:>12.2f}",
        ]
        for pago in pagos:
            lineas.append(f"Pago: {pago.metodo.value}")
            for etiqueta, valor in pago.datos_ticket():
                if isinstance(valor, Decimal):
                    lineas.append(f"{etiqueta:<28}{valor:>12.2f}")
                else:
                    lineas.append(f"{etiqueta}: {valor}")
        lineas.append("¡Gracias por su visita!")
        return "\n".join(lineas)