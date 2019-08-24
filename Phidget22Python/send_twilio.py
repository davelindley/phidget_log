from twilio.rest import Client

account_sid = "ACa7a7645f77888a8af5f3a7177ab412a6"
auth_token = "8e2e705dcbafbc0ad177c1ed5cfaa177"
client = Client(account_sid, auth_token)

def send_twilio(doneness):

    message = client.messages \
                    .create(
                         body=f'Hey big boy, you meat has {doneness} chews. ;)',
                         from_='+19143807998',
                         to='+9145525631'
                     )

    print(message.sid)

    return


