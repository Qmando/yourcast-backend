import webapp2
from google.appengine.ext import db
import struct, pickle, random, json
import datetime

inactive_delta = datetime.timedelta(0, 3*60*60) # Three hours

class Event(db.Model):
        event_id = db.IntegerProperty(required=True)
        session_num = db.IntegerProperty(required=True)
        event_str = db.StringProperty(required=True)

class Session(db.Model):
        name = db.StringProperty(required=True)
        number = db.IntegerProperty(required=True)
        creator = db.StringProperty(required=True)
        events = db.IntegerProperty(required=True)
        last_event = db.DateTimeProperty(auto_now=True)
        team1 = db.StringProperty(required=True)
        team2 = db.StringProperty(required=True)
        time = db.StringProperty(required=True)
        game_info = db.StringProperty(required=True)

def Packet(ptype, usernum=None, session_num=None, event=None,
           msg=None, event_id=None):
        packet = {}
        packet['type'] = ptype
        if usernum is not None:
                packet['user_id'] = usernum
        if session_num is not None:
                packet['session_num'] = session_num
                print "adding num", session_num
        if msg is not None:
                packet['msg'] = msg
        if event_id is not None:
                packet['event_id'] = event_id
        if event is not None:
                packet['event']=event
        return json.dumps(packet)

def get_session(number):
        session = db.GqlQuery("SELECT * FROM Session WHERE number=%d" %(number))
        for x in session:
                return x
        return None

def generate_session():
        number = random.randint(1, 2147483646)
        session = db.GqlQuery("SELECT * FROM Session WHERE number=%d" %(number))
        while session.count() > 0:
                print "DERP", session, number
                number = random.randint(1, 2147483646)
                session = db.GqlQuery("SELECT * FROM Session WHERE number=%d" %(number))
        return number

def generate_event_id(session):
        number = random.randint(1, 2147483646)
        event = db.GqlQuery("SELECT * FROM events WHERE number=%d" %(number))
        while event.count() > 0:
                number = random.randint(1, 2147483646)
                event = db.GqlQuery("SELECT * FROM Event WHERE number=%d" %(number))
        return number

def send_exception(data):
        print "Exception", data
        packet = Packet(PTYPE_EXCEPTION, msg=data)
        return packet
        
def send_session_confirm(number):
        packet = Packet(PTYPE_CREATE, session_num=number)
        print "Sending", packet
        return packet
        
def send_event_confirm(number):
        packet = Packet(PTYPE_CONFIRM, session_num=number)
        print "Sending", packet
        return packet

def send_sessions():
        sessions = db.GqlQuery("SELECT * FROM Session")
        now=datetime.datetime.now()
        session_dict = {}
        for session in sessions:
                if now-session.last_event < inactive_delta:
                        session_dict[session.name]=session.number
        json_str = json.dumps(session_dict)
        print "Sending session list", json_str
        packet = Packet(PTYPE_GET_SESSIONS, msg=json_str)
        return packet

def send_success(stuff):
        
        self.response.write('hi')

def add_event(event_str, session):
        event_id = session.events
        session.events += 1
        event = Event(event_id = event_id, event_str = event_str, session_num=session.number)
        db.put(event)
        db.put(session)

def send_uptodate():
        packet = Packet(PTYPE_UPTODATE)
        print "Sending", packet
        return packet

def get_events(session_num, event_id, info):
        events = db.GqlQuery("SELECT * FROM Event WHERE event_id >= %d AND session_num = %d"
                                %(event_id, session_num))
        num = 0
        max_event = 0
        resp = {"type": PTYPE_EVENT, "game_info": info}
        if events.count() == 0:
                return send_uptodate()
        for event in events:
                resp['event'+str(num)] = event.event_str
                num+=1
                if event.event_id > max_event:
                        max_event = event.event_id
        resp['event_id']=max_event+1
        print "sending events", json.dumps(resp)
        return json.dumps(resp)

def send_info(session):
        resp = {}
        resp['type'] = "get_info"
        resp['name'] = session.name
        resp['home team'] = session.team1
        resp['away team'] = session.team2
        resp['time'] = session.time
        resp['sport'] = 'edu.umich.yourcast.rugby'
        return json.dumps(resp)
        
PTYPE_CREATE = "create_session"
PTYPE_BROADCAST = "broadcast"
PTYPE_POLL = "poll"
PTYPE_UPTODATE = "up_to_date"
PTYPE_EVENT = "event"
PTYPE_NEWUSER = "new_user"
PTYPE_EXCEPTION = "exception"
PTYPE_CONFIRM = "confirm_event"
PTYPE_GET_SESSIONS = "get_sessions"
        
class Handler(webapp2.RequestHandler):

        def post(self):
                data = self.request.get('data')
        
                if data is None:
                        send_exception('Illegal post')
                
                try:
                        msg = json.loads(data)
                except:
                        print "Couldnt unserialize", msg
                        resp = send_exception(addr, 'Invalid packet')
                        self.response.write(resp)
                        return

                print "Got packet", data
                

                print "packet type", msg['type']
                
                if msg['type'] == 'poll':
                        session_num = msg['session_num']
                        session = get_session(session_num)
                        if session is None:
                                resp = send_exception('Session does not exist')
                                self.response.write(resp)
                                return
                        
                        event_id = msg['event_id']
                        print "Received poll for session", session_num
                        resp = get_events(session_num, event_id, session.game_info)
                        self.response.write(resp)

                
                if msg['type'] == 'broadcast':
                        session_num = msg['session_num']
                        session = get_session(session_num)
                        print "Received broadcast", msg['event'], "for session", session_num
                        
                        if session is None:
                                resp = send_exception('Session does not exist')
                                self.response.write(resp)
                                return
                                
                        if session.creator != msg['password']:
                                print session.creator, "is not", msg['password']
                                resp = send_exception('You are not session creator')
                                self.response.write(resp)
                                return
                        
                        try:
                                event = msg['event']
                        except:
                                send_exception('Invalid event')
                        
                        print "Adding event to session", session.name
                        session.game_info = msg['game_info']
                        add_event(event, session)
                        resp = send_event_confirm(session_num)
                        self.response.write(resp)
                
                if msg['type'] == "create_session":
                        name = msg['msg']
                        session_num = generate_session()
                        session = Session(name=name, creator=msg['password'], number=session_num, events=0,
                                          team1=msg['team1'], team2=msg['team2'], time=msg['time'], game_info = "{}")
                        print "Creating session", session_num, name, "user", msg['password']
                        db.put(session)
                        resp=send_session_confirm(session_num)
                        self.response.write(resp)
                
                if msg['type'] == PTYPE_GET_SESSIONS:
                        resp = send_sessions()
                        self.response.write(resp)

                if msg['type'] == "get_info":
                        session_num = msg['session_num']
                        session = get_session(session_num)
                        print "getting info for session", session_num
                        resp = send_info(session)
                        self.response.write(resp)

app = webapp2.WSGIApplication([('/', Handler)], debug=True)

def main():
    app.run()

if __name__ == "__main__":
    main()
