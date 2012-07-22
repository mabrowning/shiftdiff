# vim: set expandtab:
import webapp2
import jinja2
import os
import datetime

from google.appengine.ext import db
from google.appengine.api import users

class Shift(db.Model):
    owner = db.UserProperty(auto_current_user_add=True)
    name  = db.StringProperty()
    start = db.TimeProperty()
    end   = db.TimeProperty()
    weekend = db.BooleanProperty()
    diff_rate  = db.IntegerProperty()

class Settings(db.Model):
    holidays = db.ListProperty(datetime.date)
    holiday_diff_rate = db.IntegerProperty()
    overtime_multiplier = db.FloatProperty()
    base_rate            = db.IntegerProperty()

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),"html")))

def filter_key(model):
    try:
        return model.key().id_or_name()
    except:
        return model["key"]

def filter_currency(value):
    try:
        return "%.2f"%(float(value)/100)
    except:
        return "0.00"

def datetimeformat(datetime, format='%H%M'):
    return datetime.strftime(format)

jinja_environment.filters['datetime'] = datetimeformat
jinja_environment.filters['key'] = filter_key
jinja_environment.filters['currency'] = filter_currency

class Index(webapp2.RequestHandler):
    def get(self):
        template_values = { }
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))

class Config(webapp2.RequestHandler):
    def new_shift(self):
        return [{ "key":"new","start":datetime.time(0,0),"end":datetime.time(0,0),"diff_rate":0,"weekend":False}]
    def get(self):
        shifts = Shift.all().filter("owner =", users.get_current_user() ).run()
        settings = Settings.get_or_insert( users.get_current_user().user_id() )
        shifts = list(shifts) + self.new_shift()
        template_values = { "shifts":shifts, "settings":settings}
        template = jinja_environment.get_template('config.html')
        self.response.out.write(template.render(template_values))
    def post(self):
        shifts = Shift.all().filter("owner =", users.get_current_user() ).run()
        settings = Settings.get_or_insert( users.get_current_user().user_id() )
        showshifts =  []
        for shift in shifts:
            if self.get_shift( shift ):
                showshifts.append(shift)
        shift = Shift()
        if self.get_shift( shift ):
            showshifts.append(shift)
        shifts = showshifts + self.new_shift()


        settings.holiday_diff_rate = self.get_currency( "holiday_diff_rate")
        settings.base_rate = self.get_currency( "base_rate")
        try:
            settings.overtime_multiplier = float(self.request.get("overtime_multiplier"))
        except ValueError:
            settings.overtime_multiplier = 1.00
        settings.holidays = []
        for date in self.request.get_all("holidays"):
            try:
                settings.holidays.append( datetime.datetime.strptime(date,"%m/%d/%Y"))
            except:
                pass
        settings.save()


        template_values = { "shifts":shifts, "settings":settings}
        template = jinja_environment.get_template('config.html')
        self.response.out.write(template.render(template_values))

    def get_shift(self,shift):
        try:
            key = str(shift.key().id_or_name())
        except db.NotSavedError:
            key = "new"

        shift.name = self.request.get(key+"name")

        start = self.get_int( key+"start")
        shift.start = datetime.time(start/100,start%100)

        end = self.get_int( key+"end")
        shift.end = datetime.time(end/100,end%100)

        shift.weekend = len(self.request.get(key+"weekend")) > 0

        if key == "new":
            if len(shift.name):
                shift.save()
                return True
        else:
            if len(shift.name):
                shift.save()
                return True
            else:
                shift.delete()
        return False
    def get_int(self, name):
        try:
            return int(self.request.get(name))
        except ValueError:
            return 0
    def get_currency(self, name):
        try:
            return int(100*float(self.request.get(name)))
        except ValueError:
            return 0

app = webapp2.WSGIApplication([
    ('/', Index),
    ('/config', Config),
    ], 
    debug=True)
