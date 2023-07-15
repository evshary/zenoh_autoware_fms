const api_server = "http://127.0.0.1:8000";

/*******************************************
 *  For dynamic created buttons.
 *******************************************/
function status_on_click(scope) {
    $.ajax({
        type: "GET",
        url: `${api_server}/status/${scope}`,
        success: function(data) {
            var info = `CPU overview  (${scope})`;

            info += `\n    * Idle:        ${data.cpu.all.idle}%`;
            info += `\n    * In use:    ${data.cpu.all.total}%`;
            info += `\n    * System:  ${data.cpu.all.sys}%`;
            info += `\n    * User:       ${data.cpu.all.usr}%`;
            info += `\nVehicle status  (${scope})`;
            info += `\n    * Turn:     ${data.vehicle.status.turn_signal.data}`;
            info += `\n    * Gear:     ${data.vehicle.status.gear_shift.data}`;
            info += `\n    * Steering:    ${data.vehicle.status.steering.data}`;
            info += `\n    * Velocity:    ${data.vehicle.status.twist.linear.x}`;

            alert(info);
            console.log(data);
        },
        error: function(error) {
            console.log(error);
        },
    });
}

/*******************************************
 *  Function called periodically.
 *******************************************/
function teleop_status() {
    const scope = $('#teleop-scope').text();
    if(scope != '---'){
        $.ajax({
            type: "GET",
            url: `${api_server}/teleop/status`,
            success: function(data) {
                var vel = data.velocity * 3.6;
                $('#teleop-status-velocity').text(`${vel} km/hr`);
                $('#teleop-status-gear').text(`${data.gear}`);
                $('#teleop-status-steer').text(`${data.steering}`);
                // console.log(data);
            },
            error: function(error) {
                console.log(error);
            },
        });
    }
    else{
        alert('Please startup teleop first.');
    }
}

function teleop_set_angle() {
    const scope = $('#teleop-scope').text();
    if(scope != '---'){
        if(!isNaN($('#target-angle-text').text())){
            var sign = 1;
            if($('#target-turn-text').text() == 'Left'){
                sign = -1;
            }
            const angle = sign * $('#target-angle-text').text();

            $.ajax({
                type: "GET",
                url: `${api_server}/teleop/turn?scope=${scope}&angle=${angle}`,
                success: function(data) {
                    console.log(data);
                },
                error: function(error) {
                    console.log(error);
                },
            });
        }
    }
    else {
        alert('Please startup teleop first.');
    }
}



function teleop_startup_on_click(scope) {
    $.ajax({
        type: "GET",
        url: `${api_server}/teleop/startup?scope=${scope}`,
        success: function(data) {
            console.log(data);
            $('#teleop-scope').text(scope);
            $('#teleop-status-velocity').text('---');
            $('#teleop-status-gear').text('---');
            $('#teleop-status-steer').text('---');
            $('#target-turn-text').text('---');
            $('#target-angle-text').text('---');

            setInterval(teleop_status, 1000);
            setInterval(teleop_set_angle, 300);
            alert(data);
        },
        error: function(error) {
            console.log(error);
        },
    });
}

/*******************************************
 *  For static buttons.
 *******************************************/
$(document).ready(function() {
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
            url: `${api_server}/list`,
            dataType: "json",
            success: function(data) {
                $('#autoware-scope-list').empty();
                for(var i = 0 ; i < data.length ; i ++){
                    const status_btn_tag = `<button id='scope-link-${data[i].scope}' onclick="status_on_click('${data[i].scope}')">Status</button>`
                    const teleop_btn_tag = `<button id='scope-link-${data[i].scope}' onclick="teleop_startup_on_click('${data[i].scope}')">Teleop</button>`
                    $('#autoware-scope-list').append(`<li>${data[i].scope}<ul><li>Address: ${data[i].address}</li><li>${status_btn_tag}</li><li>${teleop_btn_tag}</li></ul></li>`);
                }
                console.log(data);
            },
            error: function(error) {
                console.log(error);
            },
        });
    });

    $('#teleop-set-gear').click( function() {
        const scope = $('#teleop-scope').text();
        const gear = $('#teleop-gear-selector').val();
        $('#teleop-gear-selector').val('None');
        if(scope != '---'){
            $.ajax({
                type: "GET",
                url: `${api_server}/teleop/gear?scope=${scope}&gear=${gear}`,
                success: function(data) {
                    // alert(data);
                },
                error: function(error) {
                    console.log(error);
                },
            });
        }
        else {
            alert('Please startup teleop first.');
        }
    });

    $('#teleop-set-velocity').click( function() {
        const scope = $('#teleop-scope').text();
        const velocity = $('#teleop-velocity-text').val();
        $('#teleop-velocity-text').val('');
        if(scope != '---'){
            if(!isNaN(velocity)){
                $.ajax({
                    type: "GET",
                    url: `${api_server}/teleop/velocity?scope=${scope}&velocity=${velocity}`,
                    success: function(data) {
                        // alert(data);
                    },
                    error: function(error) {
                        console.log(error);
                    },
                });
            }
            else{
                alert(`Velocity should be a neumeraic value. ${velocity} is not a neumeric value.`);
            }
        }
        else {
            alert('Please startup teleop first.');
        }
    });

    $('#teleop-set-steering').click( function() {
        const scope = $('#teleop-scope').text();
        const angle = $('#teleop-steering-text').val();
        if(scope != '---'){
            $('#teleop-steering-text').val('');
            if(!isNaN(angle)){
                var turn = 'None';
                if(angle < 0) turn = 'Left';
                else if(angle > 0) turn = 'Right';
                $('#target-turn-text').text(turn);
                $('#target-angle-text').text(Math.abs(angle)); 
                console.log(data);
            }
            else{
                alert(`Steering angle should be a neumeraic value. ${velocity} is not a neumeric value.`);
            }
        }
        else {
            alert('Please startup teleop first.');
        }
    });
});


