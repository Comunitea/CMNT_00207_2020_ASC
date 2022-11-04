odoo.define("stock_traceability_report_widget.ReportWidgetAt", function (require) {
    "use strict";

    var ReportWidgets = require("stock.ReportWidget");
    var core = require("web.core");
    var QWeb = core.qweb;

    ReportWidgets = ReportWidgets.extend({
        autounfold: function (target, lot_name) {
            var self = this;
            var $CurretElement;
            $CurretElement = $(target)
                .parents("tr")
                .find("td.o_stock_reports_unfoldable");
            var active_id = $CurretElement.data("id");
            var active_model_name = $CurretElement.data("model");
            var active_model_id = $CurretElement.data("model_id");
            var row_level = $CurretElement.data("level");
            var $cursor = $(target).parents("tr");
            this._rpc({
                model: "stock.traceability.report",
                method: "get_lines",
                args: [parseInt(active_id, 10)],
                kwargs: {
                    model_id: active_model_id,
                    model_name: active_model_name,
                    level: parseInt(row_level) + 30 || 1,
                    active_lot_name: lot_name,
                },
            }).then(function (lines) {
                // After loading the line
                _.each(lines, function (line) {
                    // Render each line
                    $cursor.after(QWeb.render("report_mrp_line", {l: line}));
                    $cursor = $cursor.next();
                    if ($cursor && line.unfoldable && line.lot_name == lot_name) {
                        self.autounfold($cursor.find(".fa-caret-right"), lot_name);
                    }
                });
            });
            $CurretElement.attr("class", "o_stock_reports_foldable " + active_id); // Change the class, and rendering of the unfolded line
            $(target)
                .parents("tr")
                .find("span.o_stock_reports_unfoldable")
                .replaceWith(QWeb.render("foldable", {lineId: active_id}));
            $(target).parents("tr").toggleClass("o_stock_reports_unfolded");
        },
        unfold: function (e) {
            this.autounfold($(e.target));
        },
    });
});
