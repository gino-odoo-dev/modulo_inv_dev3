import base64
from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError # type: ignore
from odoo.exceptions import ValidationError, UserError # type: ignore
import logging

# Configurar el logger
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template'

    cl_long_model = fields.Char(string="Long Model")
    cl_short_model = fields.Char(string="Short Model")

class Color(models.Model):
    _name = 'cl.product.color' 
    _description = 'Color' 
    
    name = fields.Char(string="Color")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    code = fields.Char(string="Codigo Color", required=True, size=2)

class Cantidad(models.Model):    
    _name = 'product.cantidad' 
    _description = 'Cantidad' 
    
    name = fields.Float(string="Cantidad", default=0.0)

class Tallas(models.Model):
    _name = 'cl.product.tallas'
    _description = 'Tallas'
    
    name = fields.Char(string="Talla")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)

class ProductExtensionWizard(models.TransientModel):
    _name = 'product.extension.wizard'  
    _description = 'Product Extension Wizard'  

    pdf_file = fields.Binary(string="PDF de Etiqueta", readonly=True)
    pdf_filename = fields.Char(string="Nombre del Archivo")
    cantidad = fields.Integer(string="Cantidad", default=0)
    zpl_content = fields.Text(string="ZPL Content", readonly=True) 
    
    numeracion = fields.Many2one('cl.product.tallas', string="Numeracion", required=True)
    color = fields.Many2one('cl.product.color', string="Color", required=False)
    cl_long_model = fields.Many2one('product.template', string="Modelo Largo", required=False)
    cl_short_model = fields.Many2one('product.template', string="Modelo Corto", required=False, domain="['|', ('id', '=', cl_long_model.id), ('id', '!=', False)]")

    zpl_format = fields.Selection(
        selection=[
            ('format1', 'Formato 1'),
            ('format2', 'Formato 2'),
            ('format3', 'Formato 3'),
        ],
        string="Formato de Etiqueta",
        default='format1',
        required=True
    )

    @api.constrains('zpl_format', 'color', 'numeracion', 'cantidad')
    def _check_required_fields(self):
        for record in self:
            if record.cantidad <= 0:
                raise ValidationError(_("La cantidad debe ser mayor a cero para cualquier formato"))            
            if record.zpl_format == 'format3':
                if not record.numeracion:
                    raise ValidationError(_("El campo Numeracion es requerido para el formato seleccionado"))
                if not record.cl_long_model:
                    raise ValidationError(_("El campo codigo largo es requerido para el formato seleccionado"))
                
    def _get_color(self):
        self.ensure_one()
        if not self.cl_long_model or not self.cl_long_model.cl_long_model:
            return ''   
        long_model = self.cl_long_model.cl_long_model.strip()
        if len(long_model) < 2:
            return ''  
        color_code = long_model[-2:].upper()
        try:
            color = self.env['cl.product.color'].search([('code', '=', color_code)], limit=1)
            if not color:
                _logger.warning("No se encontro color con codigo: %s", color_code)
                return color_code
            return color.name
        except Exception as e:
            _logger.error("Error buscando color: %s", str(e))
            return color_code

    def generate_zpl_label(self):
        self.ensure_one()
        
        if not self._context.get('bypass_validation'):
            self._check_required_fields()

        numeracion = self.numeracion.name if self.numeracion else ''
        cantidad = max(1, self.cantidad) 
        color = self._get_color()   
        cl_long_model = self.cl_long_model.cl_long_model if (self.cl_long_model and self.cl_long_model.cl_long_model) else ''
        cl_short_model = cl_long_model[:8] if cl_long_model else '' 
        
        _logger.debug("Generando ZPL con valores: Numeración=%s, Color=%s, Modelo Corto=%s, Modelo Largo=%s",
                    numeracion, color, cl_short_model, cl_long_model)

        format_templates = {
            'format1': "",
            'format2': """
^XA
^BY2,3,,
^PRD
^CI10
^LH0,0
^FO35,35^GB760,1170,5^FS
^FO45,45^GB740,1150,5^FS
^FO720,60^A0R,40,40^FDRemite :^FS
^FO720,850^A0R,40,40^FDFecha :^FS
^FO670,850^A0R,40,40^FD07/03/2025^FS
^FO550,60^A0R,50,50^FDNombre:^FS
^FO500,60^A0R,50,50^FDDireccion:^FS
^FO450,60^A0R,50,50^FDCiudad:^FS
^FO400,60^A0R,50,50^FDTemporada:^FS
^FO350,60^A0R,50,50^FDArticulo:^FS
^FO305,60^A0R,40,40^FDCuero:^FS
^FO255,60^A0R,40,40^FDColor:^FS
^FO110,60^A0R,45,45^FDPares:^FS
^FO215,60^A0R,40,40^FDNota de Venta:^FS
^FO215,500^A0R,40,40^FDO. Compra:^FS
^FO160,60^A0R,50,50^FDO. Fabricacion:^FS
^FO500,960^A0R,35,35^FDguia de entrada:^FS
^FO720,320^A0R,50,50^FD{}^FS
^FO670,320^A0R,50,50^FD{}^FS
^FO620,320^A0R,50,50^FD{}{}^FS
^FO550,320^A0R,50,50^FD{}^FS
^FO500,320^A0R,50,50^FD{}^FS
^FO450,320^A0R,50,50^FD{}^FS
^FO400,320^A0R,50,50^FD{}^FS
^FO350,320^A0R,50,50^FD{}^FS
^FO305,320^A0R,40,40^FDKENT.^FS
^FO255,320^A0R,40,40^FD{}^FS
^FO110,210^A0R,45,45^FD3^FS
^FO110,300^A0R,40,23^FD36E 37E 38E^FS
^FO075,290^A0R,40,32^FD1 1 1^FS
^FO215,320^A0R,40,40^FD{}^FS
^FO215,720^A0R,40,40^FD^FS
^FO160,370^A0R,50,50^FD{}^FS
^FO400,980^A0R,80,50^FD{}^FS
^FO70,950^B3N,N,100,Y^FD{}^FS
^PQ1
^MCY
^XZ
            """, 
            'format3': """
^XA
^FX
^CF0,50
^FX
^FO90,40^FD{color}^FS
^FX
^LRY
^FO290,20^GB290,90,90^FS
^CF0,70
^FO290,30^FD{cl_short_model}^FS
^FX
^BY2,3,,^FO110,123^BCN,80,N,N,N^FD{cl_long_model}{numeracion}^FS
^FX SKU.
^FO160,210^A0N,30,40^FD{cl_long_model}{numeracion}^FS
^XZ
"""     .strip()
        }

        template = format_templates.get(self.zpl_format, "").strip()
        
        zpl_content = ""
        for _ in range(cantidad):
            zpl_content += template.format(
                numeracion=numeracion,
                color=color,
                cl_short_model=cl_short_model,
                cl_long_model=cl_long_model,
            ) + "\n" 
        
        _logger.debug("Contenido ZPL generado:\n%s", zpl_content)
        return zpl_content.strip()

    def generador_txt_zpl(self):
        self.ensure_one()
        
        try:
            zpl = self.generate_zpl_label()
            if not zpl:
                raise UserError(_("Formato de etiqueta no válido"))
            model_name = self.cl_long_model.cl_long_model if self.cl_long_model else 'Etiqueta'
            filename = f"ZPL_{model_name}_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            txt_content = base64.b64encode(zpl.encode('utf-8'))
            self.write({
                'zpl_content': zpl,
                'pdf_file': txt_content,
                'pdf_filename': filename
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content?model=product.extension.wizard&id={self.id}&field=pdf_file&filename_field=pdf_filename&download=true",
                'target': 'self',
            }
        except Exception as e:
            _logger.error("Error al generar ZPL: %s", str(e), exc_info=True)
            raise UserError(_("Error al generar el archivo: %s") % str(e))