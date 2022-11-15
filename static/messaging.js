//long poll the server for new messages

//assemble endpoint from cookies
var server = document.cookie.split('; ').find(row => row.startsWith('server=')).split('=')[1];
var channel = document.cookie.split('; ').find(row => row.startsWith('channel=')).split('=')[1];

//long poll the server for new messages
async function getMessages() {
    // if this is the first time the function is called, set the last message id to 0
    var last = 0;
    if (typeof getMessages.last !== 'undefined') {
        last = getMessages.last;
    }
    console.log("endpoint: /api/" + server + "/" + channel + "/" + last);
    // otherwise, set it to the last message id in the list
    await fetch("/api/" + server + "/" + channel + "/" + last)
        .then(response => response.json())
        .then(data => {
            console.log("Messages", data);
            // for each message, create a new div with the details of the message
            // and append it to the div with id "message-list"
            for (let i = 0; i < data.length; i++) {
                var message = data[i];
                var messageDiv = document.createElement("div");
                messageDiv.className = "message-entry";
                messageDiv.innerHTML = "<h2>" + message.body + "</h2><p>" + message.content + "</p>";
                document.getElementById("message-list").appendChild(messageDiv);
            }
        })
}

//getMessages();
