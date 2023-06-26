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
                    $('#autoware-scope-list').append(`<li><a href="">${data[i].scope}</a><ul><li>address: ${data[i].address}</li></ul></li>`);
                }
                console.log(data);
            },
            error: function(error) {
                console.log(error);
            },
        });
    });
});
