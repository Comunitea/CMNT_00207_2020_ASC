# © 2020 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from prestapyt.prestapyt import PrestaShopWebServiceError


class ProductTemplateImporter(Component):

    _inherit = "prestashop.product.template.importer"

    def deactivate_default_product(self, binding):
        if binding.product_variant_count != 1:
            for product in binding.with_context(
                    active_test=True).product_variant_ids:
                if not product.attribute_value_ids:
                    self.env['product.product'].browse(product.id).orderpoint_ids.write(
                        {'active': False})
        return super().deactivate_default_product(binding)

    def _import_dependencies(self):
        res = super()._import_dependencies()
        self._import_brand()
        return res

    def _import_brand(self):
        record = self.prestashop_record
        if record.get('id_manufacturer') and record.get('id_manufacturer') not in ('0', 0):
            try:
                self._import_dependency(record['id_manufacturer'],
                                        'prestashop.product.brand')
            except PrestaShopWebServiceError as e:
                return

    def _after_import(self, binding):
        super()._after_import(binding)
        if not binding.odoo_managed_bom:
            self.import_bundles(binding)

    def import_bundles(self, binding):
        record = self._get_prestashop_data()
        if record["type"]["value"] == "simple" or record["tipo_pack"] == "1":
            if binding.bom_ids.filtered(lambda r: not r.product_id):
                # en el pasado fue un pack, eliminamos lista de materiales
                binding.sudo().bom_ids.filtered(lambda r: not r.product_id).unlink()
            return
        if record.get("associations", {}).get("product_bundle", {}).get("product", {}):
            bundle_products = {}
            binder = self.binder_for("prestashop.product.template")
            product_lines = (
                record.get("associations").get("product_bundle").get("product")
            )
            if type(product_lines) is dict:
                product_lines = [product_lines]
            for product_line in product_lines:
                self._import_dependency(
                    product_line["id"], "prestashop.product.template"
                )
                bundle_products[
                    binder.to_internal(product_line["id"], unwrap=True)
                ] = product_line["quantity"]
            create_bom = False
            if bundle_products:
                if binding.bom_ids:
                    current_bom = binding.bom_ids[0]
                    for line in current_bom.bom_line_ids:
                        if (
                            line.product_id.product_tmpl_id
                            not in bundle_products.keys()
                            or line.product_qty
                            != bundle_products[line.product_id.product_tmpl_id]
                        ):
                            binding.bom_ids.write({"active": False})
                            create_bom = True
                            break
                    for in_product in bundle_products.keys():
                        if in_product not in current_bom.mapped(
                            "bom_line_ids.product_id.product_tmpl_id"
                        ):
                            binding.bom_ids.write({"active": False})
                            create_bom = True
                            break
                else:
                    create_bom = True
                if create_bom:
                    self.env['stock.warehouse.orderpoint'].search(
                        [('product_id', 'in',
                          binding.odoo_id.product_variant_ids._ids)]).unlink()
                    self.env["mrp.bom"].create(
                        {
                            "product_tmpl_id": binding.odoo_id.id,
                            "type": "phantom",
                            "bom_line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": x.product_variant_id.id,
                                        "product_qty": bundle_products[x],
                                    },
                                )
                                for x in bundle_products.keys()
                            ],
                        }
                    )

    def import_images(self, binding):
        prestashop_record = self._get_prestashop_data()
        associations = prestashop_record.get("associations", {})
        images = associations.get("images", {}).get(
            self.backend_record.get_version_ps_key("image"), {}
        )
        if not isinstance(images, list):
            images = [images]
        if images:
            images = [images[0]]
        for image in images:
            if image.get("id"):
                delayable = self.env["prestashop.product.image"].with_context(company_id=self.backend_record.company_id.id).with_delay(priority=10)
                delayable.import_product_image(
                    self.backend_record, prestashop_record["id"], image["id"]
                )


class TemplateMapper(Component):
    _inherit = "prestashop.product.template.mapper"

    @mapping
    def standard_price(self, record):
        return {}

    @mapping
    def taxes_id(self, record):
        taxes = self._get_tax_ids(record)
        if taxes:
            return {"taxes_id": [(6, 0, taxes.ids)]}

    @mapping
    def prestashop_unique_id(self, record):
        return {"prestashop_unique_id": record["id"]}

    @only_create
    @mapping
    def odoo_id(self, record):
        template_exists = self.env["product.template"].search(
            [("prestashop_unique_id", "=", record["id"])]
        )
        if template_exists:
            return {"odoo_id": template_exists.id}
        return {}

    @mapping
    def product_brand_id(self, record):
        if record.get('id_manufacturer') and record.get('id_manufacturer') not in ('0', 0):
            brand_binder = self.binder_for("prestashop.product.brand")
            brand = brand_binder.to_internal(
                record["id_manufacturer"], unwrap=True
            )
            if brand:
                return {'product_brand_id': brand.id}
