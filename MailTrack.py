from    AppKit          import NSBundle
from    Foundation      import NSLog
from    mailtrack        import *
import  objc

class MailTrack(objc.runtime.MVMailBundle):

    @classmethod
    def initialize(cls):
        # instantiate updater
        updater = Updater()

        # register ourselves
        objc.runtime.MVMailBundle.registerBundle()

        # extract plugin version from Info.plist
        bundle  = NSBundle.bundleWithIdentifier_('pt.barraca.MailTrack')
        version = bundle.infoDictionary().get('CFBundleVersion', '??')

        # initialize app
        app = App(version, updater)

        # initialize our posing classes with app instance
        DocumentEditor.registerMailTrackApplication(app)
        MessageHeaders.registerMailTrackApplication(app)
        MailApp.registerMailTrackApplication(app)
        MailTrackPreferencesController.registerMailTrackApplication(app)
        CustomizedAttribution.registerMailTrackApplication(app)

        # announce that we have loaded
        NSLog("MailTrack Plugin (version %s) registered with Mail.app" % version)
