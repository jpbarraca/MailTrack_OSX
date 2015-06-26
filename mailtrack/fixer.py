from    AppKit                  import NSRunAlertPanel, NSAlternateKeyMask, NSEvent, NSKeyDown, NSControlKeyMask, MessageViewer
from    Foundation              import NSLog
from    mailtrack.utils          import swizzle
from    mailtrack.attribution    import CustomizedAttribution
from    mailtrack.messagetypes   import *
from    objc                    import Category, lookUpClass
from    logger                  import logger
import  re, traceback, objc

DOMText = lookUpClass('DOMText')

MailApp = lookUpClass('MailApp')
class MailApp(Category(MailApp)):

    @classmethod
    def registerMailTrackApplication(cls, app):
        cls.app = app

    @swizzle(MailApp, 'sendEvent:')
    def sendEvent(self, original, event):
        if not hasattr(self, 'app'):
            original(self, event)
            return
        self.app.toggle_key_active = False
        # keep track of an active option key
        flags = event.modifierFlags()
        if (flags & NSAlternateKeyMask) and not (flags & NSControlKeyMask):
            self.app.toggle_key_active = True
            # handle reply/reply-all (XXX: won't work if you have assigned
            # a different shortcut key to these actions!)
            if event.type() == NSKeyDown and event.charactersIgnoringModifiers().lower() == 'r':
                # strip the Option-key from the event
                event = NSEvent.keyEventWithType_location_modifierFlags_timestamp_windowNumber_context_characters_charactersIgnoringModifiers_isARepeat_keyCode_(
                    event.type(),
                    event.locationInWindow(),
                    event.modifierFlags() & ~NSAlternateKeyMask,
                    event.timestamp(),
                    event.windowNumber(),
                    event.context(),
                    event.characters(),
                    event.charactersIgnoringModifiers(),
                    event.isARepeat(),
                    event.keyCode()
                )
        original(self, event)

# our own DocumentEditor implementation
DocumentEditor = lookUpClass('DocumentEditor')
class DocumentEditor(Category(DocumentEditor)):

    @classmethod
    def registerMailTrackApplication(cls, app):
        cls.app = app

    @swizzle(DocumentEditor, 'finishLoadingEditor')
    def finishLoadingEditor(self, original):
        logger.debug('DocumentEditor finishLoadingEditor')

        # execute original finishLoadingEditor()
        original(self)

        try:
            # if toggle key is active, temporarily switch the active state
            is_active = self.app.toggle_key_active ^ self.app.is_active

            # check if we can proceed
            if not is_active:
                logger.debug("MailTrack is not active, so no MailTracking for you!")
                return

            # grab composeView instance (this is the WebView which contains the
            # message editor) and check for the right conditions
            try:
                view = objc.getInstanceVariable(self, 'composeWebView')
            except:
                # was renamed in Lion
                view = objc.getInstanceVariable(self, '_composeWebView')

            # grab some other variables we need to perform our business
            backend     = self.backEnd()
            htmldom     = view.mainFrame().DOMDocument()
            htmlroot    = htmldom.documentElement()
            messageType = self.messageType()

            # XXX: hack alert! if message type is DRAFT, but we can determine this
            # is actually a Send Again action, adjust the message type.
            origmsg = backend.originalMessage()
            if origmsg and messageType == DRAFT:
                # get the message viewer for this message
                viewer = MessageViewer.existingViewerShowingMessage_(origmsg)
                if not viewer:
                    # XXX: this happens with conversation view active, not sure if this is stable enough though
                    messageType = SENDAGAIN
                elif viewer:
                    # get the mailbox for the viewer
                    mailboxes = viewer.selectedMailboxes()
                    # get the Drafts mailbox
                    draftmailbox = viewer.draftsMailbox()
                    # check if they're the same; if not, it's a Send-Again
                    if draftmailbox not in mailboxes:
                        messageType = SENDAGAIN

            # send original HTML to menu for debugging
            self.app.html = htmlroot.innerHTML()

            if not self.app.is_mailtracking:
                logger.debug('mailtracking turned off in preferences, skipping that part')
            elif messageType not in self.app.message_types_to_track:
                logger.debug('message type "%s" not in %s, not tracking' % (
                    messageType,
                    self.app.message_types_to_track
                ))
            else:
                # move cursor to end of document
                view.moveToEndOfDocument_(self)


                # perform some general cleanups
                logger.debug('calling cleanup_layout()')
                if self.cleanup_layout(htmlroot, backend):
                    backend.setHasChanges_(False)

                # move cursor to end of document
                if self.app.move_cursor_to_top:
                    view.moveToBeginningOfDocument_(self)

            # move to beginning of line
            logger.debug('calling view.moveToBeginningOfLine()')
            view.moveToBeginningOfLine_(self)

            # done
            logger.debug('MailTracking done')
        except Exception:
            logger.critical(traceback.format_exc())
            if self.app.is_debugging:
                NSRunAlertPanel(
                    'MailTrack caught an exception',
                    'The MailTrack plug-in caught an exception:\n\n' +
                    traceback.format_exc() +
                    '\nPlease contact the developer quoting the contents of this alert.',
                    None, None, None
                )

