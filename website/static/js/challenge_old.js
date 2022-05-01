// written by debuglog#0028
// if you have any questions feel free to ask me :)

async function showAlert(message, category) {
    const alertCategoryIndex = {
        1: "info",
        2: "success",
        3: "warning",
        4: "danger"
    };
    const alertBox = document.getElementById("status");
    category = (alertCategoryIndex[category] || "info");
    alertBox.className = `text-${category}`;
    alertBox.innerText = message;
}

async function restart() {
    window.top.location = window.top.location;
}

// captcha functions
async function getPublicKey(index) {
    const publicKeyIndex = {
        1: "ACTION_TYPE_ASSET_COMMENT",
        2: "ACTION_TYPE_CLOTHING_ASSET_UPLOAD",
        3: "ACTION_TYPE_FOLLOW_USER",
        4: "ACTION_TYPE_GROUP_JOIN",
        5: "ACTION_TYPE_GROUP_WALL_POST",
        6: "ACTION_TYPE_SUPPORT_REQUEST",
        7: "ACTION_TYPE_WEB_GAMECARD_REDEMPTION",
        8: "ACTION_TYPE_WEB_LOGIN",
        9: "ACTION_TYPE_WEB_RESET_PASSWORD",
        10: "ACTION_TYPE_WEB_SIGNUP"
    };
    const url = "https://apis.rbxcdn.com/captcha/v1/metadata";
    let response = await fetch(url);
    if (response.status === 200) {
        let json = await response.json();
        let publicKey = json["funCaptchaPublicKeys"][publicKeyIndex[index]];
        return publicKey;
    } else {
        await showAlert(`Couldn't fetch the public key.\nStatus: ${response.status}`, 4);
        return false;
    }
}

async function getCaptchaJob() {
    const url = "/api/captcha/job";
    let response = await fetch(url);
    if (response.status === 200) {
        let json = await response.json();
        let captchaJob = json["job"];
        return captchaJob;
    } else if (response.status === 202 || response.status === 401) {
        let json = await response.json();
        let message = json["message"];
        await showAlert(message, 3);
        return false;
    } else {
        await showAlert(`Couldn't fetch a job.\nStatus: ${response.status}`, 4);
        return false;
    }
}

let captchaId = null;
async function captchaSolved(captchaToken) {
    const url = "/api/captcha/submit";
    let data = new URLSearchParams();
    data.set("id", captchaId);
    data.set("token", captchaToken);
    const options = {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: data
    };
    let response = await fetch(url, options);
    const allowedStatusArray = [200, 202, 400];
    if (allowedStatusArray.includes(response.status)) {
        const statusCategoryIndex = {
            200: 2,
            202: 3,
            400: 3,
            500: 4
        };
        let json = await response.json();
        let message = json["message"];
        await showAlert(message, statusCategoryIndex[response.status]);
    } else {
        await showAlert(`Something went wrong.\nStatus: ${response.status}`, 4);
    }
    return setTimeout(restart, 2000);
}

async function showCaptcha(publicKey, captchaData) {
    FunCaptcha({
        public_key: publicKey,
        target_html: "captcha",
        data: {
            blob: captchaData
        },
        callback: captchaSolved
    });
    await showAlert("Solve the following captcha")
}

async function main() {
    let captchaJob = await getCaptchaJob();
    if (captchaJob) {
        let captchaIndex = captchaJob["key"];
        let captchaData = captchaJob["data"];
        captchaId = captchaJob["id"];
        let publicKey = await getPublicKey(captchaIndex);
        if (publicKey) {
            showCaptcha(publicKey, captchaData);
        }
    }
}

window.addEventListener("load", main);