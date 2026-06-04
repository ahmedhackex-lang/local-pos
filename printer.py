"""
Thermal printer integration for receipt printing
ESC/POS protocol support with multiple connection types
"""

from typing import Dict, List, Optional
import platform
from decimal import Decimal
from datetime import datetime
from config import settings
import logging

logger = logging.getLogger(__name__)


# Conditional imports based on platform
try:
    from escpos.printer import Usb, Serial, Network, Dummy
    if platform.system() == 'Windows':
        from escpos.printer import Win32Raw
        import win32print
except ImportError:
    logger.warning("ESC/POS library not available. Printing will be disabled.")
    Usb = Serial = Network = Win32Raw = Dummy = None
    win32print = None


class PrinterManager:
    """
    Manages thermal printer connections and receipt printing
    Supports USB, Serial, Network, and Windows printer drivers
    """
    
    def __init__(self):
        self.active_printer = None
        self.printer_type = None
        self.printer_config = {}
        self.is_available = False
    
    def discover_windows_printers(self) -> List[str]:
        """
        Discover all installed Windows printers
        
        Returns:
            List of printer names
        """
        if platform.system() != 'Windows' or win32print is None:
            return []
        
        printers = []
        try:
            for printer_info in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            ):
                printers.append(printer_info[2])  # Printer name
        except Exception as e:
            logger.error(f"Failed to enumerate printers: {e}")
        
        return printers
    
    def configure_usb_printer(self, vendor_id: int, product_id: int):
        """
        Configure USB thermal printer
        
        Args:
            vendor_id: USB Vendor ID (hex)
            product_id: USB Product ID (hex)
        """
        if Usb is None:
            raise Exception("ESC/POS library not available")
        
        try:
            self.active_printer = Usb(vendor_id, product_id)
            self.printer_type = "usb"
            self.printer_config = {
                "vendor_id": vendor_id,
                "product_id": product_id
            }
            self.is_available = True
            logger.info(f"USB printer configured: {vendor_id:04x}:{product_id:04x}")
        except Exception as e:
            logger.error(f"USB printer configuration failed: {e}")
            raise
    
    def configure_serial_printer(self, port: str, baudrate: int = 9600):
        """
        Configure Serial (COM port) printer
        
        Args:
            port: COM port (e.g., "COM1", "/dev/ttyUSB0")
            baudrate: Baud rate (default: 9600)
        """
        if Serial is None:
            raise Exception("ESC/POS library not available")
        
        try:
            self.active_printer = Serial(port, baudrate=baudrate)
            self.printer_type = "serial"
            self.printer_config = {
                "port": port,
                "baudrate": baudrate
            }
            self.is_available = True
            logger.info(f"Serial printer configured: {port} @ {baudrate}")
        except Exception as e:
            logger.error(f"Serial printer configuration failed: {e}")
            raise
    
    def configure_network_printer(self, ip_address: str, port: int = 9100):
        """
        Configure network printer (Ethernet/WiFi)
        
        Args:
            ip_address: Printer IP address
            port: TCP port (default: 9100 for raw printing)
        """
        if Network is None:
            raise Exception("ESC/POS library not available")
        
        try:
            self.active_printer = Network(ip_address, port=port)
            self.printer_type = "network"
            self.printer_config = {
                "ip_address": ip_address,
                "port": port
            }
            self.is_available = True
            logger.info(f"Network printer configured: {ip_address}:{port}")
        except Exception as e:
            logger.error(f"Network printer configuration failed: {e}")
            raise
    
    def configure_windows_printer(self, printer_name: str):
        """
        Configure Windows printer driver
        
        Args:
            printer_name: Name of installed Windows printer
        """
        if Win32Raw is None:
            raise Exception("Windows printer support not available")
        
        try:
            self.active_printer = Win32Raw(printer_name)
            self.printer_type = "windows"
            self.printer_config = {
                "printer_name": printer_name
            }
            self.is_available = True
            logger.info(f"Windows printer configured: {printer_name}")
        except Exception as e:
            logger.error(f"Windows printer configuration failed: {e}")
            raise
    
    def print_receipt(self, sale_data: Dict) -> bool:
        """
        Print sales receipt
        
        Args:
            sale_data: Dictionary containing sale information
            
        Returns:
            True if print successful, False otherwise
        """
        if not self.is_available or self.active_printer is None:
            logger.warning("Printer not configured. Skipping print.")
            return False
        
        try:
            p = self.active_printer
            
            # Initialize printer
            p.hw('INIT')
            
            # ===== HEADER =====
            p.set(align='center', font='a', bold=True, width=2, height=2)
            p.text(f"{settings.STORE_NAME}\n")
            
            p.set(align='center', font='a', bold=False, width=1, height=1)
            p.text(f"{settings.STORE_ADDRESS}\n")
            p.text(f"{settings.STORE_CITY}\n")
            p.text(f"Tel: {settings.STORE_PHONE}\n\n")
            
            p.text("=" * 42 + "\n\n")
            
            # ===== INVOICE DETAILS =====
            p.set(align='left', font='a', bold=False)
            p.text(f"Invoice: {sale_data['invoice_number']}\n")
            p.text(f"Date: {sale_data['date']}\n")
            p.text(f"Cashier: {sale_data['cashier_name']}\n")
            
            if sale_data.get('customer_name'):
                p.text(f"Customer: {sale_data['customer_name']}\n")
            
            p.text("\n" + "-" * 42 + "\n")
            
            # ===== COLUMN HEADERS =====
            p.set(font='a', bold=True)
            header = f"{'ITEM':<20} {'QTY':>3} {'PRICE':>7} {'TOTAL':>7}\n"
            p.text(header)
            p.text("-" * 42 + "\n")
            
            # ===== LINE ITEMS =====
            p.set(bold=False)
            for item in sale_data['items']:
                # Truncate long product names
                name = item['name'][:20].ljust(20)
                qty = f"{item['quantity']:>3.0f}" if item['quantity'] % 1 == 0 else f"{item['quantity']:>3.2f}"
                price = f"{float(item['price']):>7.2f}"
                total = f"{float(item['subtotal']):>7.2f}"
                
                line = f"{name} {qty} {price} {total}\n"
                p.text(line)
            
            p.text("-" * 42 + "\n\n")
            
            # ===== TOTALS =====
            p.set(align='right', font='a', bold=False)
            
            subtotal = float(sale_data['total_amount'])
            discount = float(sale_data.get('discount', 0))
            tax = float(sale_data.get('tax_amount', 0))
            net_amount = float(sale_data['net_amount'])
            
            p.text(f"Subtotal: {subtotal:>10.2f}\n")
            
            if discount > 0:
                p.text(f"Discount: {discount:>10.2f}\n")
            
            if tax > 0:
                p.text(f"Tax: {tax:>10.2f}\n")
            
            p.text("=" * 42 + "\n")
            
            # ===== NET TOTAL =====
            p.set(align='center', font='a', bold=True, width=2, height=2)
            p.text(f"TOTAL: {settings.CURRENCY} {net_amount:.2f}\n")
            p.text("=" * 42 + "\n\n")
            
            # ===== PAYMENT DETAILS =====
            p.set(align='left', font='a', bold=False, width=1, height=1)
            payment_method = sale_data['payment_method']
            p.text(f"Payment Method: {payment_method}\n")
            
            if payment_method == 'Cash':
                tendered = float(sale_data.get('amount_tendered', 0))
                change = float(sale_data.get('change_returned', 0))
                
                p.text(f"Amount Tendered: {settings.CURRENCY} {tendered:.2f}\n")
                p.text(f"Change: {settings.CURRENCY} {change:.2f}\n")
            
            p.text("\n" + "=" * 42 + "\n\n")
            
            # ===== FOOTER =====
            p.set(align='center', font='a', bold=True)
            p.text("Thank You For Shopping!\n")
            p.text("Please Come Again\n\n")
            p.text("=" * 42 + "\n\n")
            
            # ===== CUT PAPER =====
            p.cut()
            
            logger.info(f"Receipt printed: {sale_data['invoice_number']}")
            return True
            
        except Exception as e:
            logger.error(f"Print failed: {e}")
            return False
    
    def print_test_receipt(self) -> bool:
        """
        Print a test receipt to verify printer configuration
        
        Returns:
            True if successful, False otherwise
        """
        test_data = {
            'invoice_number': 'TEST-0001',
            'date': datetime.now().strftime("%d/%m/%Y %I:%M %p"),
            'cashier_name': 'Test User',
            'total_amount': Decimal('100.00'),
            'discount': Decimal('0.00'),
            'tax_amount': Decimal('0.00'),
            'net_amount': Decimal('100.00'),
            'payment_method': 'Cash',
            'amount_tendered': Decimal('100.00'),
            'change_returned': Decimal('0.00'),
            'items': [
                {
                    'name': 'Test Product',
                    'quantity': Decimal('1'),
                    'price': Decimal('100.00'),
                    'subtotal': Decimal('100.00')
                }
            ]
        }
        
        return self.print_receipt(test_data)
    
    def open_cash_drawer(self) -> bool:
        """
        Send cash drawer open command (ESC/POS)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available or self.active_printer is None:
            logger.warning("Printer not configured. Cannot open cash drawer.")
            return False
        
        try:
            # ESC/POS command to open cash drawer
            # ESC p m t1 t2 (0x1B 0x70 0x00 0x19 0x19)
            self.active_printer._raw(b'\x1B\x70\x00\x19\x19')
            logger.info("Cash drawer opened")
            return True
        except Exception as e:
            logger.error(f"Failed to open cash drawer: {e}")
            return False


# Global printer manager instance
printer_manager = PrinterManager()


def init_printer_from_settings():
    """
    Initialize printer from application settings
    Called during application startup
    """
    if not settings.PRINTER_ENABLED:
        logger.info("Printer disabled in settings")
        return
    
    try:
        printer_type = settings.PRINTER_TYPE.lower()
        
        if printer_type == "windows":
            if settings.PRINTER_NAME:
                printer_manager.configure_windows_printer(settings.PRINTER_NAME)
            else:
                # Auto-detect first available printer
                printers = printer_manager.discover_windows_printers()
                if printers:
                    printer_manager.configure_windows_printer(printers[0])
                    logger.info(f"Auto-configured printer: {printers[0]}")
        
        elif printer_type == "network":
            # Example: configure from environment or config
            # printer_manager.configure_network_printer("192.168.1.100", 9100)
            logger.warning("Network printer requires manual configuration")
        
        elif printer_type == "usb":
            # Example: configure from environment or config
            # printer_manager.configure_usb_printer(0x04b8, 0x0e03)
            logger.warning("USB printer requires manual configuration")
        
        elif printer_type == "serial":
            # Example: configure from environment or config
            # printer_manager.configure_serial_printer("COM1", 9600)
            logger.warning("Serial printer requires manual configuration")
        
    except Exception as e:
        logger.error(f"Printer initialization failed: {e}")