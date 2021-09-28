function matchCustom(params, data) {
    if(data==='No está en la lista' || data==='Not in List'){
        return data;
    }
    if ($.trim(params) === '') {
      return data;
    }
    if (data.toUpperCase().indexOf(params.toUpperCase()) > -1) {
        return data
    }

    // Return `null` if the term should not be displayed
    return null;
}

odoo.define("rma_portal.custom", function (require) {
    "use strict";
    require("web.dom_ready");
    var ajax = require("web.ajax");
    var rma_obj = $(".rma_add_object_page");

    $(document).on("click", ".remove_rma_line", function () {
        $(this).parent().parent().parent().remove();
    });
    $(document).on("click", ".rma_add_line_btn", function () {
        $("body").append("<div class='add_rma_loader'/>");
        ajax.jsonRpc("/my/add_rma_line", "call", {}).then(function (result) {
            $(".rma_line_tbody").append(result);
            $(".rma_line_tbody select").select2({
                placeholder: 'Select a product',
                allowClear: true,
                matcher: matchCustom
              })
            $(".add_rma_loader").remove();
        });
    });
    $(document).on("click", ".submit_rma_obj", function () {
        var delivery_address = $(".rma_add_object_page")
            .find("select[name='delivery_address']")
            .val();
        var pickup_date = $("#pickup_time_from").val();
        var list = [];
        var objlist = [];
        var with_errors = false;
        if($("#operation_type_return")[0].checked ===true){
            var order_id = $(".rma_add_object_page").find("select[name='order_reference']").val();
            if(!order_id){
                $(".rma_add_object_page").find("select[name='order_reference']").addClass("is-invalid");
                $("#s_website_form_result").addClass("text-danger ml8");
                $("#s_website_form_result").html('<i class="fa fa-close mr4" role="img" aria-label="Error" title="Error"></i>Please fill in the form correctly.');
                with_errors = true;
            }
            else{
                $(".rma_add_object_page").find("select[name='order_reference']").removeClass("is-invalid");
                $("#s_website_form_result").removeClass("text-danger ml8");
                $("#s_website_form_result").html('');
            }
        }
        else{
            if (!pickup_date) {
                $("#pickup_time_from").addClass("is-invalid");
                $("#s_website_form_result").addClass("text-danger ml8");
                $("#s_website_form_result").html('<i class="fa fa-close mr4" role="img" aria-label="Error" title="Error"></i>Please fill in the form correctly.');
                with_errors = true;
            } else {
                $("#pickup_time_from").removeClass("is-invalid");
                $("#s_website_form_result").removeClass("text-danger ml8");
                $("#s_website_form_result").html('');
            }
            if (!delivery_address) {
                $(".rma_add_object_page")
                    .find("select[name='delivery_address']")
                    .addClass("is-invalid");
                $("#s_website_form_result").addClass("text-danger ml8")
                $("#s_website_form_result").html('<i class="fa fa-close mr4" role="img" aria-label="Error" title="Error"></i>Please fill in the form correctly.')
                with_errors = true;
            } else {
                $(".rma_add_object_page")
                    .find("select[name='delivery_address']")
                    .removeClass("is-invalid");
                    $("#s_website_form_result").removeClass("text-danger ml8")
                    $("#s_website_form_result").html('')
            }

        }
        if(!$("#privacy_policy").prop("checked")){
            $("#privacy_policy_label").addClass("is-invalid");
            $("#s_website_form_result").addClass("text-danger ml8")
            $("#s_website_form_result").html('<i class="fa fa-close mr4" role="img" aria-label="Error" title="Error"></i>Please fill in the form correctly.')
            with_errors = true;
        } else {
            $("#privacy_policy_label").removeClass("is-invalid");
            $("#s_website_form_result").removeClass("text-danger ml8")
            $("#s_website_form_result").html('')
        }

        if (with_errors===true) {
            return;
        }
        objlist = {
        };
        if($("#operation_type_return")[0].checked ===true){
            objlist['operation_type'] = 'return'
            objlist['order_id'] = $(".rma_add_object_page").find("select[name='order_reference']").val();
        }
        else{
            objlist['operation_type'] = 'rma'
            objlist['return_delivery_address'] = parseInt(delivery_address);
            objlist['pickup_date'] = $(".rma_add_object_page").find("input[name='date']").val()
            objlist['pickup_hour'] = $("#pickup_time_from").val();
            objlist['timezone'] = new Date().getTimezoneOffset() / 60
        }
        var list_of_tr = $(".rma_add_object_page").find(".rma_line_tbody tr");
        var rma_line_required = false;

        $(".rma_add_object_page")
            .find(".rma_line_tbody tr")
            .each(function (res) {
                var product_id = $(list_of_tr[res])
                    .find("select[name='product_id']")
                    .val();
                var product_ref = $(list_of_tr[res])
                    .find("input[name='not_in_list']")
                    .val();

                if (product_id == "-1" && product_ref == "") {
                    rma_line_required = true;
                    $(list_of_tr[res])
                        .find("input[name='not_in_list']")
                        .addClass("is-invalid");
                } else {
                    $(list_of_tr[res])
                        .find("input[name='not_in_list']")
                        .removeClass("is-invalid");
                }

                if (product_id) {
                    var qty = $(list_of_tr[res]).find("input[name='qty']").val();
                    var searial_num = $(list_of_tr[res])
                        .find("input[name='serial_num']")
                        .val();
                    var note = $(list_of_tr[res]).find("input[name='note']").val();
                    list.push({
                        pid: parseInt(product_id),
                        qty: parseInt(qty),
                        searial_num: searial_num,
                        note: note,
                        product_ref: product_ref,
                    });
                }
                // List.push()
            });

        if (rma_line_required) {
            return;
        }

        var shipping_name = $(".rma_add_object_page")
            .find("input[name='shipping_name']")
            .val();
        var shipping_phone = $(".rma_add_object_page")
            .find("input[name='shipping_phone']")
            .val();
        var shipping_street = $(".rma_add_object_page")
            .find("input[name='shipping_street']")
            .val();
        var shipping_city = $(".rma_add_object_page")
            .find("input[name='shipping_city']")
            .val();
        var shipping_zip = $(".rma_add_object_page")
            .find("input[name='shipping_zip']")
            .val();
        var shipping_country_id = $(".rma_add_object_page")
            .find("select[name='shipping_country_id']")
            .val();
        var shipping_state_id = $(".rma_add_object_page")
            .find("select[name='shipping_state_id']")
            .val();
        var shipping_mobile = $(".rma_add_object_page")
            .find("input[name='shipping_mobile']")
            .val();
        var shipping_email = $(".rma_add_object_page")
            .find("input[name='shipping_email']")
            .val();
        var shipping_note = $(".rma_add_object_page")
            .find("input[name='shipping_note']")
            .val();
        var optVal = $("#delivery_address option:selected").val();

        var shipping_data = {
            shipping_name: shipping_name,
            shipping_phone: shipping_phone,
            shipping_street: shipping_street,
            shipping_city: shipping_city,
            shipping_zip: shipping_zip,
            shipping_country_id: parseInt(shipping_country_id),
            shipping_state_id: parseInt(shipping_state_id),
            shipping_note: shipping_note,
            shipping_mobile: shipping_mobile,
            shipping_email: shipping_email,
            optVal: parseInt(optVal),
        };

        $("body").append("<div class='add_rma_loader'/>");
        $("body").append("<div class='loader_rma_obj'/>");
        ajax.jsonRpc("/my/create_rma_obj", "call", {
            rma_obj: objlist,
            rma_line: list,
            shipping_data: shipping_data,
        }).then(function (result) {
            if (result) {
                $(".loader_rma_obj").remove();
                $(".add_rma_loader").remove();
                window.location.href = "/my/thanks_rma_msg?rma_obj=" + result;
            } else {
                $(".loader_rma_obj").remove();
                $(".add_rma_loader").remove();
            }
        });
    });
    $(rma_obj).on("change", "#pickup_time_from", function () {
        var hour_from = $('#pickup_time_from').val();
        if(parseInt(hour_from.substring(0,2)) < 9 || parseInt(hour_from.substring(0,2)) > 17){
            $("#pickup_time_from").addClass("is-invalid");
            $("#from_pickup_time_error").addClass("text-danger ml8");
            $("#from_pickup_time_error").html('<i class="fa fa-close mr4" role="img" aria-label="Error" title="Error"></i>Should be between 09:00-17:00.');
        }
        else{
            $("#pickup_time_from").removeClass("is-invalid");
            $("#from_pickup_time_error").removeClass("text-danger ml8");
            $("#from_pickup_time_error").html('');
            var hour_to = (parseInt(hour_from.substring(0,2)) + 3).toString().concat(hour_from.substring(2,5));
            $('#pickup_time_to').val(hour_to);
        }
    });
    $(rma_obj).on("change", "input[type=radio][name=operation_type]", function () {
        if(this.value == 'return'){
            $('#return_info').show();
            $('#rma_info').hide();
            // $('.submit_rma_obj').addClass('disabled');

        }
        else{
            $('#return_info').hide();
            $('#rma_info').show();
            // $('.submit_rma_obj').removeClass('disabled');

        }
    });
    $('.datepicker').datepicker({
        startDate: '+1d',
        endDate: '+30d',
        language: 'es',
        daysOfWeekDisabled: [0,6]
    });

    // $(document).on("click", ".rma_check_order", function () {
    //     var order_reference = $('#order_reference').val();
    //     var message_div = $('#return_info_message');
    //     message_div.attr('class', 'col-3');
    //     message_div.empty()
    //     ajax.jsonRpc("/my/check_order_date", "call", {
    //         order_ref: order_reference,
    //     }).then(function (result) {
    //         if((!result && result != 0) || result == -1){
    //             message_div.addClass('alert alert-danger');
    //             $('.submit_rma_obj').addClass('disabled');
    //             message_div.append( "<span>Order not found</span>" );
    //         }
    //         else if(result < 30){
    //             message_div.addClass('alert alert-success');
    //             $('.submit_rma_obj').removeClass('disabled');
    //             message_div.append( "<span>The order can be returned</span>" );

    //         }
    //         else if(result < 60){
    //             message_div.addClass('alert alert-warning');
    //             $('.submit_rma_obj').removeClass('disabled');
    //             message_div.append( "<span>The return should be approved manually</span>" );
    //         }
    //         else{
    //             message_div.addClass('alert alert-danger');
    //             $('.submit_rma_obj').addClass('disabled');
    //             message_div.append( "<span>The return can't be created</span>" );

    //         }
    //     });
    // });
});
