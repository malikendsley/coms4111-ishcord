// get channel list for the server
async function getChannels() {
    var fid = document.cookie.split('; ').find(row => row.startsWith('server=')).split('=')[1];
    //console.log("fid: " + fid);
    await fetch("/api/" + fid + "/channels")
        .then(response => response.json())
        .then(data => {
            console.log("Channels", data);
            // for each channel, create a new div with the details of the channel
            // and append it to the div with id "channel-list"
            for (let i = 0; i < data.length; i++) {
                var channel = data[i];
                var channelDiv = document.createElement("div");
                channelDiv.className = "channel-entry";
                // strip quotes from the channel name
                channelDiv.id = "channel-" + channel.cname;
                channelDiv.innerHTML = "<h2>" + channel.cname + "</h2><p>" + channel.topic + "</p>";
                document.getElementById("channel-list").appendChild(channelDiv);
            }
            // create a new div that when clicked, will redirect to dashboard with the server id in the url
            var channelEntries = document.getElementsByClassName("channel-entry");
            for (let i = 0; i < channelEntries.length; i++) {
                channelEntries[i].addEventListener("click", function () {
                    window.location.href = "/dashboard/" + fid + "/" + data[i].cname;
                })
            }
        
            var channel = document.cookie.split('; ').find(row => row.startsWith('channel=')).split('=')[1];
            channel = channel.replaceAll("\"", "");
            console.log("looking for channel-" + channel);
            var selectedChannel = document.getElementById("channel-" + channel);
            if (selectedChannel != null) {
                selectedChannel.className = "channel-entry selected";
            }
            else {
                console.log("channel not found");
            }
        })
}

getChannels();