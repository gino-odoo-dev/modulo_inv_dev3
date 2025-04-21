import base64
import logging
from odoo import models, fields, api, _ # type: ignore
from odoo.exceptions import UserError, ValidationError # type: ignore
from odoo.tools import html2plaintext # type: ignore

_logger = logging.getLogger(__name__)

class ProductTemplateExtension(models.Model):
    _inherit = 'product.template'
    
    cl_long_model = fields.Char(string="Long Model")
    cl_short_model = fields.Char(string="Short Model")

class ProductColor(models.Model):
    _name = 'cl.product.color'
    _description = 'Product Color'
    
    name = fields.Char(string="Color", required=True)
    code = fields.Char(string="Codigo Color", required=True, size=2)
    company_id = fields.Many2one('res.company', string="Compañia", default=lambda self: self.env.company, required=True)

class ProductQuantity(models.Model):
    _name = 'product.cantidad'
    _description = 'Product Quantity'
    
    name = fields.Float(string="Cantidad", default=0.0)

class ProductSize(models.Model):
    _name = 'cl.product.tallas'
    _description = 'Product Size'
    
    name = fields.Char(string="Size", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)

class PurchaseOrderExtension(models.Model):
    _inherit = 'purchase.order'
    
    name = fields.Char(string="Nombre Compañia")

class ResCompanyExtension(models.Model):
    _inherit = 'res.company'
    
    name = fields.Char(string="Nombre Compañia")
    company_details = fields.Html(string="Compañia Detalles")

class ProductLabelWizard(models.TransientModel):
    _name = 'product.extension.wizard'
    _description = 'Product Label Wizard'
    
    pdf_file = fields.Binary(string="Label PDF", readonly=True)
    pdf_filename = fields.Char(string="Filename")
    zpl_content = fields.Text(string="ZPL Content", readonly=True)
    
    cantidad = fields.Integer(string="Quantity", default=0)
    zpl_format = fields.Selection(
        selection=[
            ('format1', 'Format 1'), 
            ('format2', 'Format 2'), 
            ('format3', 'Format 3')
        ], 
        string="Label Format", 
        default='format1',
        required=True
    )
    
    numeracion = fields.Many2one('cl.product.tallas', string="Size")
    color = fields.Many2one('cl.product.color', string="Color")
    cl_long_model = fields.Many2one('product.template', string="Long Model")
    cl_short_model = fields.Many2one('product.template', string="Short Model", domain="['|', ('id', '=', cl_long_model.id), ('id', '!=', False)]")
    
    orden_compra = fields.Many2one('purchase.order', string="Purchase Order")
    nombre_orden = fields.Char(string="Order Name", compute="_compute_order_name", store=True)    
    company_id = fields.Many2one('res.company', string="Company")
    detalle_compañia = fields.Text(string="Company Details", compute="_compute_company_details", readonly=True)
    cl_temporada_id = fields.Many2one('cl.product.temporada', string="Temporada", compute="_compute_temporada", store=True)
    cl_articulos_id = fields.Char(string="Articulo", compute="_compute_articulo_info", store=True)
    cl_color_id = fields.Many2one('cl.product.color', string="Color del Producto", compute="_compute_color_from_order", store=True, readonly=True)
    cl_ofabricacion_id = fields.Many2one('mrp.production', string="Orden de Fabricación", compute="_compute_ofabricacion", store=True, readonly=True)

    @api.depends('orden_compra')
    def _compute_ofabricacion(self):
        for wizard in self:
            wizard.cl_ofabricacion_id = False
            if wizard.orden_compra:
                order_lines = wizard.orden_compra.order_line
                if order_lines:
                    product_ids = order_lines.mapped('product_id').ids
                    if product_ids:
                        production_order = self.env['mrp.production'].search([
                            ('product_id', 'in', product_ids),
                            ('state', 'in', ['confirmed', 'progress', 'done'])  
                        ], limit=1, order='id desc')  
                        if production_order:
                            wizard.cl_ofabricacion_id = production_order

    @api.depends('orden_compra')
    def _compute_articulo_info(self):
        for record in self:
            if record.orden_compra:
                line = record.orden_compra.order_line.filtered(
                    lambda l: l.product_id.cl_long_model
                )[:1]
                record.cl_articulos_id = line.product_id.cl_long_model if line else ''
            else:
                record.cl_articulos_id = ''

    @api.depends('orden_compra')
    def _compute_temporada(self):
        for record in self:
            if record.orden_compra:
                line = record.orden_compra.order_line.filtered(
                    lambda l: l.product_id.cl_temporada_id
                )[:1]
                record.cl_temporada_id = line.product_id.cl_temporada_id if line else False
            else:
                record.cl_temporada_id = False

    @api.depends('orden_compra')
    def _compute_order_name(self):
        for record in self:
            record.nombre_orden = record.orden_compra.company_id.name if (
                record.orden_compra and 
                record.orden_compra.company_id
            ) else ''

    @api.depends('company_id')
    def _compute_company_details(self):
        for record in self:
            if record.company_id and record.company_id.company_details:
                clean_text = html2plaintext(record.company_id.company_details)
                record.detalle_compañia = ' '.join(clean_text.split()).strip()[:150] 
            else:
                record.detalle_compañia = ''

    @api.constrains('zpl_format', 'color', 'numeracion', 'cantidad', 'orden_compra')
    def _check_required_fields(self):
        for record in self:
            if record.cantidad <= 0:
                raise ValidationError(_("Quantity must be greater than zero"))
            
            if record.zpl_format == 'format2' and not record.orden_compra:
                raise ValidationError(_("Purchase order is required for this format"))
            
            if record.zpl_format == 'format3':
                if not record.numeracion:
                    raise ValidationError(_("Size is required for this format"))
                if not record.cl_long_model:
                    raise ValidationError(_("Long model is required for this format"))

    def _get_color_from_model(self):
        self.ensure_one()
        if not self.cl_long_model or not self.cl_long_model.cl_long_model:
            return ''
            
        long_model = self.cl_long_model.cl_long_model.strip()
        if len(long_model) < 2:
            return ''
            
        color_code = long_model[-2:].upper()
        try:
            color = self.env['cl.product.color'].search([('code', '=', color_code)], limit=1)
            return color.name if color else color_code
        except Exception as e:
            _logger.error("Color search error: %s", str(e))
            return color_code

    def _generate_zpl_content(self):
        self.ensure_one()
        
        if not self._context.get('bypass_validation'):
            self._check_required_fields()

        template_vars = {
            'numeracion': self.numeracion.name if self.numeracion else '',
            'color': self._get_color_from_model(),
            'cl_long_model': self.cl_long_model.cl_long_model if (
                self.cl_long_model and 
                self.cl_long_model.cl_long_model
            ) else '',
            'cl_short_model': '',
            'nombre_orden': self.nombre_orden or '',
            'orden_compra': self.orden_compra.name if self.orden_compra else '',
            'detalle_compañia': self.detalle_compañia or 'SIN DETALLES',
            'temporada': self.cl_temporada_id.name if self.cl_temporada_id else '',
            'articulo': self.cl_articulos_id if self.cl_articulos_id else '',
            'color_nombre': self.cl_color_id.name if self.cl_color_id else '',
            'orden_fabricacion': self.cl_ofabricacion_id.name if self.cl_ofabricacion_id else 'N/A',
        }
        
        if template_vars['cl_long_model']:
            template_vars['cl_short_model'] = template_vars['cl_long_model'][:8]

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
^FO720,320^A0R,50,50^FD{nombre_orden}^FS
^FO670,320^A0R,50,50^FD{detalle_compañia}^FS
^FO620,320^A0R,50,50^FD^FS
^FO550,320^A0R,50,50^FD^FS
^FO500,320^A0R,50,50^FD^FS
^FO450,320^A0R,50,50^FD^FS
^FO400,320^A0R,50,50^FD{temporada}^FS
^FO350,320^A0R,50,50^FD{articulo}^FS
^FO305,320^A0R,40,40^FDKENT.^FS
^FO255,320^A0R,40,40^FD{color_nombre}^FS
^FO110,210^A0R,45,45^FD3^FS
^FO110,300^A0R,40,23^FD36E 37E 38E^FS
^FO075,290^A0R,40,32^FD1 1 1^FS
^FO215,320^A0R,40,40^FD^FS
^FO215,720^A0R,40,40^FD{orden_compra}^FS
^FO160,370^A0R,50,50^FD{orden_fabricacion}^FS
^FO400,980^A0R,80,50^FD^FS
^FO70,950^B3N,N,100,Y^FD{orden_compra}^FS
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
""".strip()
        }

        template = format_templates.get(self.zpl_format, "").strip()
        zpl_content = ""
        for _ in range(max(1, self.cantidad)):
            zpl_content += template.format(**template_vars) + "\n"
            
        _logger.debug("Generated ZPL content:\n%s", zpl_content)
        return zpl_content.strip()

    def generate_zpl_file(self):
        self.ensure_one()
        
        try:
            zpl = self._generate_zpl_content()
            if not zpl:
                raise UserError(_("Invalid label format"))
                
            model_name = self.cl_long_model.cl_long_model if self.cl_long_model else 'Label'
            filename = f"ZPL_{model_name}.txt"
            
            self.write({
                'zpl_content': zpl,
                'pdf_file': base64.b64encode(zpl.encode('utf-8')),
                'pdf_filename': filename
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': (
                    f"/web/content?model=product.extension.wizard&id={self.id}"
                    f"&field=pdf_file&filename_field=pdf_filename&download=true"
                ),
                'target': 'self',
            }
        except Exception as e:
            _logger.error("ZPL generation error: %s", str(e), exc_info=True)
            raise UserError(_("File generation error: %s") % str(e))



