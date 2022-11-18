//long poll the forum for new messages
async function getMessages(last) {
    // if channel contains special characters, encode it
    var forum = document.cookie.split('; ').find(row => row.startsWith('forum=')).split('=')[1];
    var channel = document.cookie.split('; ').find(row => row.startsWith('channel=')).split('=')[1];
    
    let response = await fetch("/api/" + forum + "/" + channel + "/" + last);
    if (response.status == 502) {
        await getMessages(last);
    } else if (response.status != 200) {
        console.log("error");
        await new Promise(resolve => setTimeout(resolve, 1000));
        await getMessages(last);
    } else {
        let data = await response.json();
        console.log(data);
        if (data["messages"].length == 0) {
            console.log("No new messages, waiting 1 second");
            await new Promise(resolve => setTimeout(resolve, 1000));
            await getMessages(last);
        }
        if(data["success"] == false) {
            console.log("error, retrying");
            await new Promise(resolve => setTimeout(resolve, 1000));
            await getMessages(last);
        } else {
        // get the highest mid in the json
        lastmessageid = Math.max(...data["messages"].map(x => x["mid"]));
        console.log("last message id: " + lastmessageid);
        console.log(data);
        //add messages to the page in reverse order
        for (var i = data["messages"].length - 1; i >= 0; i--) {
            var message = data["messages"][i];
            var html = `
                <div class="message" id="message-${message["mid"]}">
                    <h3 style="color: #${message["color"]}; text-shadow: 1px 1px #000000;">${message["name"]}</p>
                    <p style="overflow-wrap: break-word;">${message["body"]}</p>
                    <p>${message["timestamp"]}</p>
                </div>
                `
            document.getElementById("message-list").innerHTML += html;
            }
        console.log(lastmessageid);
        // scroll to bottom of div with id 'message-list'
        document.getElementById("message-list").scrollTop = document.getElementById("message-list").scrollHeight;
        await getMessages(lastmessageid);
        }
    }
}

getMessages(0);
