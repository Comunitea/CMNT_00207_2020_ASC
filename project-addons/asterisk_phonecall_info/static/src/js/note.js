/*  # © 2020 Comunitea
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).   */

odoo.define('asterisk_phonecall_info.systray.writeNote', function (require) {
"use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var _t = core._t;

var OpenCaller = require('asterisk_click2dial.systray.OpenCaller');

OpenCaller.include({
    on_open_caller: function (event) {
        // We need to do preventDefault to stop the window from losing the current focus
        event.preventDefault();
        return this._super(event);
   },
})

var FieldPhone = require('base_phone.updatedphone_widget').FieldPhone;

FieldPhone.include({
    _renderReadonly: function() {
        var self = this;
        this._super();
        // We need to do preventDefault to stop the window from losing the current focus
        this.$('a.dial').off('click');
        this.$('a.dial').on('click', function onClick(event) {
            event.preventDefault();
            self.click2dial(this.phone_num);
        });
    },
});

var WriteNoteMenu = Widget.extend({
    name: 'write_note',
    template: 'asterisk_phonecall_info.systray.WriteNote',
    events: {
        'click': 'on_write_note',
    },

    on_write_note: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var self = this;
        var context = this.getSession().user_context;

        self._rpc({
            route: '/asterisk_click2dial/get_record_from_my_channel',
            params: {local_context: context, },
            }).then(function(r) {

        console.log("RPC");
        
        if (r === false) {
             self.do_warn(
                _t('IPBX error'),
                _t('Calling party number not retreived from IPBX or IPBX unreachable by Odoo'),
                false);
        }
        else if (typeof r == 'string' && isNaN(r)) {
             self.do_warn(
                r,
                _t('The calling number is not a phone number!'),
                false);
        }
        else if (typeof r == 'string') {
            var action = {
                name: _t('Number Not Found'),
                type: 'ir.actions.act_window',
                res_model: 'number.not.found',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {'default_calling_number': r},
             };
            self.do_action(action);
            }
        else if (typeof r == 'object' && r.length == 3) {
            var action = {
                name: _t('Add Notes to Phonecall'),
                type: 'ir.actions.act_window',
                res_model: 'phonecall.notes.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {'default_calling_number': r},
                };
            self.do_action(action);
        }
    });
   },
});

SystrayMenu.Items.push(WriteNoteMenu);

return WriteNoteMenu;

});
