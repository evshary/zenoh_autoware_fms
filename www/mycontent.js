function status_on_click(btn) {
    const scope = btn.innerHTML;
    const api_server = "http://127.0.0.1:8000/";
    $.ajax({
        type: "GET",
        url: api_server + 'status/' + scope,
        success: function(data) {
            // document.getElementById("status-text").innerHTML = data.all.status;
            var velocity = (data.vehicle.status.twist.linear.x) * (data.vehicle.status.twist.linear.x) + (data.vehicle.status.twist.linear.y) * (data.vehicle.status.twist.linear.y);
            var info = `CPU overview  (${scope})`;
            info += `\n    * Idle:        ${data.cpu.all.idle}%`;
            info += `\n    * In use:    ${data.cpu.all.total}%`;
            info += `\n    * System:  ${data.cpu.all.sys}%`;
            info += `\n    * User:       ${data.cpu.all.usr}%`;
            info += `\nVehicle status  (${scope})`;
            info += `\n    * Trun:     ${data.vehicle.status.turn_signal.data}`;
            info += `\n    * Gear:     ${data.vehicle.status.gear_shift.data}`;
            info += `\n    * Steering:    ${data.vehicle.status.steering.data}`;
            info += `\n    * Velocity:    ${velocity}`;

            alert(info);
            console.log(data);
        },
        error: function(error) {
            console.log(error);
        },
    });
}

$(document).ready(function() {
    const api_server = "http://127.0.0.1:8000/"
    $.ajax({
        type: "GET",
        url: api_server,
        dataType: "json",
        success: function(data) {
            console.log(data);
            document.getElementById("mycontent").innerHTML = data.message;
        },
        error: function(error) {
            console.log(error);
        },
    });
    $('#list-autoware-button').click( function() {
        $.ajax({
            type: "GET",
            url: api_server + 'list',
            dataType: "json",
            success: function(data) {
                $('#autoware-scope-list').empty();
                for(var i = 0 ; i < data.length ; i ++){
                    $('#autoware-scope-list').append(`<li><button id='scope-link-${data[i].scope}' onclick="status_on_click(this)">${data[i].scope}</button><ul><li>Address: ${data[i].address}</li></ul></li>`);
                }
                console.log(data);
            },
            error: function(error) {
                console.log(error);
            },
        });
    });
});


