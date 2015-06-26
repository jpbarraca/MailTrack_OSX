from    AppKit                  import NSUserDefaults, NSBundle, NSApplication, NSRunAlertPanel
from    Foundation              import NSLog
from    mailtrack.menu           import Menu
from    objc                    import Category, lookUpClass
from    logger                  import logger
import  os, re

class App(object):

    def __init__(self, version, updater):
        # set version
        self.version = version

        # set updater
        self.updater = updater

        # keep state of 'toggle key'
        self.toggle_key_active = False

        # read user defaults (preferences)
        self.prefs = NSUserDefaults.standardUserDefaults()

        # register some default values
        self.prefs.registerDefaults_(dict(
            MailTrackOption        = True,
            MailTrackEnableDebugging = False,
            MailTrackDisabled = False
        ))

        # set log level
        logger.setLevel(self.is_debugging and logger.DEBUG or logger.WARNING)
        logger.debug('debug logging active')

        # add menu item for quick enable/disable
        Menu.alloc().initWithApp_(self).inject()

        # check update interval
        self.check_update_interval = self.prefs.int["MailTrackCheckUpdateInterval"] or 0

        # check if we're running in a different Mail version as before
        self.check_version()

    def check_version(self):
        infodict    = NSBundle.mainBundle().infoDictionary()
        mailversion = infodict['CFBundleVersion']
        lastknown   = self.prefs.string["MailTrackLastKnownBundleVersion"]
        if lastknown and lastknown != mailversion:
            NSRunAlertPanel(
                'MailTrack plug-in',
                '''
The MailTrack plug-in detected a different Mail.app version (perhaps you updated?).

If you run into any problems with regards to replying or forwarding mail, consider removing this plug-in (from ~/Library/Mail/Bundles/).

(This alert is only displayed once for each new version of Mail.app)''',
                    None,
                    None,
                    None
            )
            self.prefs.string["MailTrackLastKnownBundleVersion"] = mailversion

    # used for debugging
    @property
    def html(self):
        return self._html

    @html.setter
    def html(self, html):
        self._html = html

    # return reference to main window
    def window(self):
        return NSApplication.sharedApplication().mainWindow()

    # 'is plugin active?'
    @property
    def is_active(self):
        return not self.prefs.bool["MailTrackDisabled"]

    @is_active.setter
    def is_active(self, value):
        self.prefs.bool["MailTrackDisabled"] = value

    # debugging
    @property
    def is_debugging(self):
        return self.prefs.bool['MailTrackEnableDebugging']

    # update-related properties
    @property
    def check_update_interval(self):
        return self._check_update_interval

    @check_update_interval.setter
    def check_update_interval(self, value):
        # store in preferences
        self.prefs.string["MailTrackCheckUpdateInterval"] = value
        self._check_update_interval = value

        # convert to interval and pass to updater
        if   value == 0: interval = 0 # never
        elif value == 1: interval = 7 * 24 * 60 * 60 # weekly
        elif value == 2: interval = int(4.35 * 7 * 24 * 60 * 60) # monthly
        else           : return
        self.updater.set_update_interval(interval)

    @property
    def last_update_check(self):
        return self.updater.last_update_check

    # check for updates
    def check_for_updates(self):
        self.updater.check_for_updates()

# make NSUserDefaults a bit more Pythonic
class NSUserDefaults(Category(lookUpClass('NSUserDefaults'))):

    @property
    def bool(self):     return DictProxy(self, 'bool')

    @property
    def string(self):   return DictProxy(self, 'string')

    @property
    def object(self):   return DictProxy(self, 'object')

    @property
    def int(self):      return DictProxy(self, 'int')

class DictProxy:

    def __init__(self, delegate, type):
        self.delegate   = delegate
        self.type       = type

    def __getitem__(self, item):
        return {
            'string'    : self.delegate.stringForKey_,
            'bool'      : self.delegate.boolForKey_,
            'object'    : self.delegate.objectForKey_,
            'int'       : self.delegate.integerForKey_,
        }[self.type](item)

    def __setitem__(self, item, value):
        {
            'string'    : self.delegate.setObject_forKey_, # no setString_forKey_
            'bool'      : self.delegate.setBool_forKey_,
            'object'    : self.delegate.setObject_forKey_,
            'int'       : self.delegate.setInteger_forKey_,
        }[self.type](value, item)
