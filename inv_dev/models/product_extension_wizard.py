import base64
import logging
from odoo import models, fields, api, _  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
from odoo.tools import html2plaintext  # type: ignore

_logger = logging.getLogger(__name__)

class ProductTemplateExtension(models.Model):
    _inherit = 'product.template'

    cl_long_model = fields.Char(string="Long Model")
    cl_short_model = fields.Char(string="Short Model")

class ProductColor(models.Model):
    _name = 'cl.product.color'
    _description = 'Color de Producto'

    name = fields.Char(string="Color", required=True)
    code = fields.Char(string="Codigo Color", required=True, size=2)
    company_id = fields.Many2one('res.company', string="Compañia", default=lambda self: self.env.company, required=True)

class ProductQuantity(models.Model):
    _name = 'product.cantidad'
    _description = 'Cantidad de Producto'

    name = fields.Float(string="Cantidad", default=0.0)

class ProductSize(models.Model):
    _name = 'cl.product.tallas'
    _description = 'Talla de Producto'

    name = fields.Char(string="Size", required=True)
    company_id = fields.Many2one('res.company', string="Compañia", default=lambda self: self.env.company, required=True)

class PurchaseOrderExtension(models.Model):
    _inherit = 'purchase.order'

    name = fields.Char(string="Nombre Compañia")

class ResCompanyExtension(models.Model):
    _inherit = 'res.company'

    name = fields.Char(string="Nombre Compañia")
    company_details = fields.Html(string="Compañia Detalles")

class StockLot(models.Model):
    _inherit = 'stock.lot'

    lote_desde = fields.Char(string="Lote Desde")
    lote_hasta = fields.Char(string="Lote Hasta")

class ProductLabelWizard(models.TransientModel):
    _name = 'product.extension.wizard'
    _description = 'Product Label Wizard'

    pdf_file = fields.Binary(string="Label PDF", readonly=True)
    pdf_filename = fields.Char(string="Filename")
    zpl_content = fields.Text(string="ZPL Content", readonly=True)

    cantidad = fields.Integer(string="Cantidad", default=0, required=True)
    zpl_format = fields.Selection(selection=[('format1', 'Formato 1'), ('format2', 'Formato 2'), ('format3', 'Formato 3')], string="Label Format", default='format1', required=True)

    numeracion = fields.Many2one('cl.product.tallas', string="Talla")
    color = fields.Many2one('cl.product.color', string="Color")
    cl_long_model = fields.Many2one('product.template', string="Codigo Largo")
    cl_short_model = fields.Many2one('product.template', string="Codigo Corto", domain="['|', ('id', '=', cl_long_model.id), ('id', '!=', False)]")

    orden_compra = fields.Many2one('purchase.order', string="Orden de Compra")
    nombre_orden = fields.Char(string="Nombre de Orden", compute="_compute_order_name", store=True)
    company_id = fields.Many2one('res.company', string="Compañia")
    detalle_compañia = fields.Text(string="Compañia Detalles", compute="_compute_company", readonly=True)
    cl_temporada_id = fields.Many2one('cl.product.temporada', string="Temporada", compute="_compute_temporada", store=True)
    cl_articulos_id = fields.Char(string="Articulo", compute="_compute_articulo", store=True)
    cl_color_id = fields.Many2one('cl.product.color', string="Color del Producto", compute="_get_color", store=True, readonly=True)
    cl_ofabricacion_id = fields.Many2one('mrp.production', string="Orden de Fabricacion", compute="_compute_ofabricacion", store=True, readonly=True)

    lote_desde = fields.Many2one('stock.lot', string="Lote Desde")
    lote_hasta = fields.Many2one('stock.lot', string="Lote Hasta")
    orden_compra1 = fields.Many2one('purchase.order', string="Orden de Compra")
    nombre_lote = fields.Char(string="Nombre Lote", compute="_compute_lote_name", store=True)
    color_lote = fields.Char(string="Color Lote", compute="_compute_color_lote", store=True)
    material_lote = fields.Char(string="Material Lote", compute="_compute_material_lote", store=True)
    linea_lote = fields.Char(string="Linea Lote", compute="_compute_linea_lote", store=True)
    nombre_dis = fields.Char(string="Nombre en bloque", compute="_compute_dis", store=True)
    nombre_dis2 = fields.Char(string="Nombre en bloque 2", compute="_compute_dise", store=True)

    @api.depends('nombre_dis')
    def _compute_dise(self):
        for record in self:
            record.nombre_dis2 = ''
            if record.nombre_dis:
                parts = record.nombre_dis.split('-')
                if len(parts) > 2:
                    record.nombre_dis2 = parts[2]

    @api.depends('lote_desde', 'lote_hasta')
    def _compute_dis(self):
        for record in self:
            record.nombre_dis = ''
            if record.lote_desde and record.lote_desde.product_id:
                product = record.lote_desde.product_id
                if product.default_code:
                    code = product.default_code
                    formatted_code = '-'.join([
                        code[:2], 
                        code[2:3],  
                        code[3:7], 
                        code[7:8], 
                        code[8:10],  
                        code[10:11],  
                        code[11:13],  
                        code[13:]  
                    ])
                    record.nombre_dis = formatted_code

    @api.depends('lote_desde', 'lote_hasta')
    def _compute_linea_lote(self):
        for record in self:
            record.linea_lote = ''
            if record.lote_desde and record.lote_desde.location_id:
                record.linea_lote = str(record.lote_desde.location_id.id)
            else:
                record.linea_lote = '0'

    @api.depends('lote_desde', 'lote_hasta')
    def _compute_material_lote(self):
        for record in self:
            record.material_lote = ''
            if record.lote_desde and record.lote_desde.product_id:
                product = record.lote_desde.product_id
                if hasattr(product, 'cl_material_id') and product.cl_material_id:
                    record.material_lote = product.cl_material_id.name
                elif hasattr(product, 'product_tmpl_id') and hasattr(product.product_tmpl_id, 'cl_material_id') and product.product_tmpl_id.cl_material_id:
                    record.material_lote = product.product_tmpl_id.cl_material_id.name
                else:
                    record.material_lote = 'SIN MATERIAL'

    @api.depends('lote_desde', 'lote_hasta')
    def _compute_color_lote(self):
        for record in self:
            record.color_lote = ''
            if record.lote_desde and record.lote_desde.product_id:
                product = record.lote_desde.product_id
                if hasattr(product, 'cl_color_id') and product.cl_color_id:
                    record.color_lote = product.cl_color_id.name
                elif hasattr(product, 'product_tmpl_id') and hasattr(product.product_tmpl_id, 'cl_color_id') and product.product_tmpl_id.cl_color_id:
                    record.color_lote = product.product_tmpl_id.cl_color_id.name
                else:
                    record.color_lote = 'SIN COLOR'

    @api.depends('lote_desde', 'lote_hasta')
    def _compute_lote_name(self):
        for record in self:
            record.nombre_lote = ''
            if record.lote_desde and record.lote_desde.product_id:
                record.nombre_lote = record.lote_desde.product_id.default_code or 'SIN CODIGO'

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
    def _compute_articulo(self):
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
    def _compute_company(self):
        for record in self:
            if record.company_id and record.company_id.company_details:
                clean_text = html2plaintext(record.company_id.company_details)
                record.detalle_compañia = ' '.join(clean_text.split()).strip()[:150]
            else:
                record.detalle_compañia = ''

    @api.constrains('zpl_format', 'color', 'numeracion', 'cantidad', 'orden_compra')
    def _check_required_fields(self):
        for record in self:
            if record.zpl_format == 'format1':
                if not record.lote_desde:
                    raise ValidationError(_("Debe ingresar un Lote Desde antes de generar una etiqueta"))
                if not record.lote_hasta:
                    raise ValidationError(_("Debe ingresar un Lote Hasta antes de generar una etiqueta"))

            if record.zpl_format == 'format2':
                if not record.orden_compra:
                    raise ValidationError(_("Debe ingresar una Orden de Compra antes de generar una etiqueta"))
                if record.cantidad <= 0:
                    raise ValidationError(_("Debe ingresar una cantidad mayor a cero antes de generar una etiqueta"))

            if record.zpl_format == 'format3':
                if not record.numeracion:
                    raise ValidationError(_("Debe ingresar una talla antes de generar una etiqueta"))
                if not record.cl_long_model:
                    raise ValidationError(_("Debe ingresar un SKU antes de generar una etiqueta"))
                if record.cantidad <= 0:
                    raise ValidationError(_("Debe ingresar una cantidad mayor a cero antes de generar una etiqueta"))

    @api.depends('cl_long_model')
    def _get_color(self):
        for record in self:
            record.cl_color_id = False
            if not record.cl_long_model or not record.cl_long_model.cl_long_model:
                continue

            long_model = record.cl_long_model.cl_long_model.strip()
            if len(long_model) < 2:
                continue

            color_code = long_model[-2:].upper()
            try:
                color = self.env['cl.product.color'].search([('code', '=', color_code)], limit=1)
                record.cl_color_id = color
            except Exception as e:
                _logger.error("Color search error: %s", str(e))
                record.cl_color_id = False

    def _get_orden_compra_from_lote(self, lote):
        move_line = self.env['stock.move.line'].search([
            ('lot_id', '=', lote.id),
            ('picking_id.purchase_id', '!=', False)
        ], limit=1)
        return move_line.picking_id.purchase_id if move_line else None

    def _generate_format1_zpl(self, template_vars):
        zpl_content = ""
        
        start_id = self.lote_desde.id
        end_id = self.lote_hasta.id
        
        if start_id > end_id:
            start_id, end_id = end_id, start_id
        lotes = self.env['stock.lot'].search([
            ('id', '>=', start_id),
            ('id', '<=', end_id)
        ], order='id')
        template = """
^XA
^BY2,3,,
^PRD
^CI10
^LH0,0
^FO700,170^A0R,70,70^FDCALZADO GINO^FS
^FO650,170^A0R,50,50^FDMIRAFLORES #8860^FS
^FO600,170^A0R,50,50^FDRENCA^FS
^FO550,170^A0R,50,50^FDSANTIAGO^FS
^FO95,60^B3N,N,100,Y^FD{lote_desde}^FS
^FO650,580^A0R,50,50^FDLote = {lote_desde}^FS
^FO600,580^A0R,50,50^FDO/C  = {orden_compra1}^FS
^FO550,580^A0R,50,50^FDLin  = {linea_lote}^FS
^FO500,230^A0R,40,40^FDMODELO : {nombre_lote}^FS
^FO450,230^A0R,40,40^FDCOLOR  : {color_lote}^FS
^FO400,230^A0R,40,40^FDCUERO  : {material_lote}^FS
^FO350,230^A0R,40,40^FDCODIGO : {nombre_dis}^FS
^FO400,950^A0R,60,45^FDT.PARES^FS
^FO350,950^A0R,60,45^FD  8^FS
^FO150,300^A0R,40,25^FD 35E 36E 37E 38E 39E^FS
^FO110,300^A0R,40,25^FD   1   2   2   2   1^FS
^FO020,560^A0R,90,45^FD      {nombre_dis2}^FS
^FO020,700^A0R,90,45^FD      C57^FS
^FO020,240^A0R,40,45^FD      ^FS
^XZ
^XA
^MCY
^XZ
""".strip()

        for lote in lotes:
            current_vars = template_vars.copy()
            current_vars['lote_desde'] = lote.name
            current_vars['nombre_lote'] = lote.product_id.default_code if lote.product_id and lote.product_id.default_code else 'SIN CODIGO'
            orden_compra = self._get_orden_compra_from_lote(lote)
            current_vars['orden_compra1'] = orden_compra.name if orden_compra else 'SIN OC'
            current_vars['color_lote'] = self.color_lote or 'SIN COLOR'
            current_vars['material_lote'] = self.material_lote or 'SIN MATERIAL'
            current_vars['linea_lote'] = self.linea_lote or 'SIN LINEA'
            current_vars['nombre_dis'] = self.nombre_dis or 'SIN NOMBRE'
            current_vars['nombre_dis2'] = self.nombre_dis2 or 'SIN NOMBRE 2'
            zpl_content += template.format(**current_vars) + "\n"
            
        return zpl_content

    def _generate_zpl_contenido(self):
        self.ensure_one()
        if not self._context.get('bypass_validation'):
            self._check_required_fields()

        template_vars = {
            'numeracion': self.numeracion.name if self.numeracion else '',
            'color': self.color.name if self.color else '',
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
            'orden_compra1': self.orden_compra1.name if self.orden_compra1 else '',
            'lote_desde': self.lote_desde.name if self.lote_desde else 'SIN LOTE',
            'lote_hasta': self.lote_hasta.name if self.lote_hasta else 'SIN LOTE',
            'nombre_lote': self.nombre_lote or '',
            'color_lote': self.color_lote or 'SIN COLOR',
            'material_lote': self.material_lote or 'SIN MATERIAL',
            'linea_lote': self.linea_lote or 'SIN LINEA',
            'nombre_dis': self.nombre_dis or 'SIN NOMBRE',
            
        }
        
        if template_vars['cl_long_model']:
            template_vars['cl_short_model'] = template_vars['cl_long_model'][:8]

        if self.zpl_format == 'format1':
            return self._generate_format1_zpl(template_vars)
        elif self.zpl_format == 'format2':
            template = """
^XA
^BY2,3,,
^PRD
^CI10
^LH0,0
^FO35,35^GB760,1170,5^FS
^FO45,45^GB740,1150,5^FS
^FO720,60^A0R,40,40^FDRemite :^FS
^FO720,1050^A0R,40,40^FDFecha :^FS
^FO670,950^A0R,40,40^FD07/03/2025^FS
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
^FO670,320^A0R,50,50^FDMIRAFLORES #8860 - RENCA^FS
^FO620,320^A0R,50,50^FDSANTIAGO - CHILE^FS
^FO550,320^A0R,50,50^FDFABRICA DE CALZADOS GINO SA ^FS
^FO500,320^A0R,50,50^FDAV MIRAFLORES 8860 RENCA^FS
^FO450,320^A0R,50,50^FDNUNOA^FS
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
""".strip()
            zpl_content = ""
            for _ in range(max(1, self.cantidad)):
                zpl_content += template.format(**template_vars) + "\n"
            return zpl_content
        elif self.zpl_format == 'format3':
            template = """
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
            zpl_content = ""
            for _ in range(max(1, self.cantidad)):
                zpl_content += template.format(**template_vars) + "\n"
            return zpl_content

    def generador_zpl(self):
        self.ensure_one()
        
        try:
            zpl = self._generate_zpl_contenido()
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