//long poll the server for new messages

//assemble endpoint from cookies
var server = document.cookie.split('; ').find(row => row.startsWith('server=')).split('=')[1];
var channel = document.cookie.split('; ').find(row => row.startsWith('channel=')).split('=')[1];

//long poll the server for new messages
async function getMessages(last) {
    let response = await fetch("/api/" + server + "/" + channel + "/" + last);
    if (response.status == 502) {
        await getMessages(last);
    } else if (response.status != 200) {
        console.log("error");
        await new Promise(resolve => setTimeout(resolve, 1000));
        await getMessages(last);
    } else {
        let data = await response.json();
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
                    <div style="color: #${message["color"]}">${message["name"]}</div>
                    <div>${message["body"]}</div>
                    <div>${message["timestamp"]}</div>
                </div>
                `
            document.getElementById("message-list").innerHTML += html;
            }
        console.log(lastmessageid);
        await getMessages(lastmessageid);
        }
    }
}

getMessages(0);
