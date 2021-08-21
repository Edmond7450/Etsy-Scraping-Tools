var statusTimer;

$(document).ready(function () {
    $('.sidenav').sidenav();
});

$("#btnSearch").click(function () {
    $("#btnSearch").addClass('disabled');

    $('.preloader-wrapper').addClass('active');
    $('#server_status').removeClass('hide');
    $('#btnStop').removeClass('hide');

    var form = $(this).closest("form");
    form.submit();

    statusTimer = setInterval(getStatus, 1000);
});

function getStatus() {
    $.ajax({
        url: "get_status",
        type: "GET",
        dataType: 'json',
        success: function (data) {
            $.each(data, function (name, value) {
                if (name == "status" && value) {
                    //console.log(value + "\n");
                    $('#server_status').append(value + "\n");
                    $('#server_status').animate({scrollTop: $("#server_status").prop("scrollHeight")});
                }
            });
        }
    });
}

$("#btnStop").click(function () {
    clearInterval(statusTimer);

    $.ajax({
        url: "stop_search",
        type: "POST",
        data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function (data) {
            if (data.status) {
                $('.preloader-wrapper').removeClass('active');
                $('#server_status').addClass('disabled');
                $('#btnStop').addClass('disabled');

                $('#preloader').html("<div class='progress' style='margin-top: 15px;'><div class='indeterminate'></div></div>");
            }
        }
    });
});

$("#ckb_db").change(function () {
    if ($(this).prop("checked")) $("#ckb_autonew").attr("disabled", true)
    else $("#ckb_autonew").removeAttr("disabled")
});
