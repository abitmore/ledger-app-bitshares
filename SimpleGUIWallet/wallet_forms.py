"""
Various window tabs, panels and input forms of the SimpleGUIWallet
"""

##
## Module imports:
##

# Python Standard Modules:

import webbrowser
import binascii
import string
import json
import ttk
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# Third-party:

import version as version

# Local modules:

from logger import Logger
from wallet_actions import is_valid_account_name
from wallet_actions import pprintHistoryItem
from wallet_actions import getTransactionFromHistoryItem


##
## Classes:
##

class ScrolledTextVarBound(ScrolledText):
    """
    A scrolled Text widget, but bound to a StringVar just like Entry
    widgets can do.  By default, Text widgets don't support the
    `textvariable` config option (like Entry widgets do).  So we add
    that functionality in here, including setting up necessary tracing
    and callbacks so that the two entities track each other.
    """

    def __init__(self, parent, *args, **kwargs):
        self.textvariable = kwargs.pop("textvariable", None)  # Remote tk.StringVar
        ScrolledText.__init__(self, parent, *args, **kwargs)
        # Generally, we respond when remote is updated.  Unless WE are
        # the one who updated it...
        self.watch_remote = True
        self.watch_local = True
        # Notice when remote variable changes:
        self.textvariable.trace("w", self.remote_change_callback)
        # Notice when local content changes:
        self.bind("<<Modified>>", self.on_text_modified)

    def on_text_modified(self, *args):
        """
        We "notice" text changes by catching <<Modified>> event, which is a slight
        abuse, as this is meant as event when modified from a saved state, not *each*
        and every modification.  Thus we have to set our modified flag back to False
        every time we catch.  And something is causeing this event to "bounce" - it
        gets called twice every time we actually modify, which also double-calls
        local_change_callback... for the moment this seems harmless though.
        """
        self.edit_modified(False)
        self.local_change_callback()

    def local_change_callback(self, *args):
        if self.watch_local:
            old_watch = self.watch_remote
            self.watch_remote = False
            self.textvariable.set(self.get(1.0, tk.END))
            self.watch_remote = old_watch

    def remote_change_callback(self, *args):
        if self.watch_remote:
            old_watch = self.watch_local
            self.watch_local = False
            self.delete(1.0, tk.END)
            self.insert(tk.END, self.textvariable.get())
            self.watch_local = old_watch


class ScrolledListbox(tk.Listbox):
    """
    Reusable list box with scrolling ability along two axes
    """

    def __init__(self, parent, *args, **kwargs):
        frameargs = {
            "borderwidth": kwargs.pop("borderwidth", 2),
            "relief": kwargs.pop("relief", "ridge"),
        }
        self.frame = ttk.Frame(parent, **frameargs)
        tk.Listbox.__init__(self, self.frame, *args, relief="sunken", **kwargs)
        self.v_scroll = tk.Scrollbar(self.frame, orient="vertical")
        self.v_scroll.pack(side="right", expand=False, fill="y")
        self.config(yscrollcommand=self.v_scroll.set)
        self.v_scroll.config(command=self.yview)
        self.h_scroll = tk.Scrollbar(self.frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", expand=False, fill="x")
        self.config(xscrollcommand=self.h_scroll.set)
        self.h_scroll.config(command=self.xview)

    def pack(self, *args, **kwargs):
        self.frame.pack(*args, **kwargs)
        super(ScrolledListbox, self).pack(expand=True, fill="both")


class WhoAmIFrame(ttk.Frame):
    """
    Header: Enter Account Name and Slip Path.  Refresh Balances and Copy Public Key.
    """

    def __init__(self, parent, *args, **kwargs):

        self.parent = parent
        self.button_command = kwargs.pop('command', lambda *args, **kwargs: None)
        self.textvariable = kwargs.pop('textvariable', None)
        self.textvariable_path = kwargs.pop('textvar_bip32_path', None)
        self.textvariable_key = kwargs.pop('textvar_bip32_key', None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        frame_row_1 = ttk.Frame(self)
        frame_row_1.pack(fill="x")
        frame_row_2 = ttk.Frame(self)
        frame_row_2.pack(fill="x")

        ttk.Label(frame_row_1, text="BitShares User Account:", font=("Helvetica", 16)
        ).pack(side="left")

        box_from_account_name = ttk.Entry(frame_row_1, width=30, textvariable=self.textvariable)
        box_from_account_name.pack(side="left", padx=10)
        box_from_account_name.bind("<FocusOut>", self.sender_focus_out)
        box_from_account_name.bind("<Return>", self.sender_focus_out)
        self.textvariable.trace("w", self.sender_field_on_change)

        self.button = ttk.Button(frame_row_1, text="Refresh Balances", command=lambda: self.button_handler())
        self.button.pack(side="left", padx=5, pady=(0,2))
        self.btn_copypub = ttk.Button(frame_row_1, text="Copy PubKey", command=lambda: self.btn_copy_handler())
        self.btn_copypub.pack(side="left", padx=5, pady=(0,2))

        ttk.Label(frame_row_2, text="SLIP48 Path:", font=("Helvetica", 16)).pack(side="left")
        box_bip32_path = ttk.Entry(frame_row_2, width=16, textvariable=self.textvariable_path)
        box_bip32_path.pack(side="left", padx=10)
        self.textvariable_path.trace("w", self.path_on_change)

        ttk.Label(frame_row_2, text="PubKey: ").pack(side="left")
        box_bip32_key = ttk.Entry(frame_row_2, width=48, textvariable=self.textvariable_key, state="readonly")
        box_bip32_key.pack(side="left")
        self.textvariable_key.trace("w", self.pubkey_on_change)

    def sender_field_on_change(self, *args):
        if self.sender_is_validatable():
            self.button.configure(state="normal")
        else:
            self.button.configure(state="disabled")

    def sender_is_validatable(self):
        sender_str = self.textvariable.get().strip().lower()
        return is_valid_account_name(sender_str)

    def sender_focus_out(self, *args):
        sender_str = self.textvariable.get().strip().lower()
        self.textvariable.set(sender_str)
        if not str(self.button["state"]) == "disabled":
            self.button_handler()

    def path_on_change(self, *args):
        self.textvariable_key.set("")

    def pubkey_on_change(self, *args):
        if len(self.textvariable_key.get())>0:
            self.btn_copypub.configure(state="normal")
        else:
            self.btn_copypub.configure(state="disabled")

    def btn_copy_handler(self):
        address = self.textvariable_key.get()
        self.parent.clipboard_clear()
        self.parent.clipboard_append(address)
        Logger.Clear()
        Logger.Write(("Public key %s copied to clipboard.\n" +
                      "Have you confirmed this key on your hardware device? See Public Keys tab. " +
                      "Do not add to a live account if you have not confirmed on device.") % address)

    def button_handler(self):
        self.button.configure(state="disabled")
        Logger.Clear()
        try:
            account_name = self.textvariable.get()
            if len(account_name) == 0:
                Logger.Write("Please provide an account name!")
                return
            Logger.Write("Refreshing account balances and history for '%s'..." % account_name)
            self.button_command()
        finally:
            self.button.update() # Eat any clicks that occured while disabled
            self.button.configure(state="normal") # Return to enabled state
            Logger.Write("READY.")


class AssetListFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.asset_text_var = kwargs.pop('assettextvariable', None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        self.Balances = []

        self.lst_assets = ScrolledListbox(self)
        self.lst_assets.pack(padx=2, pady=2, side="left", fill="both", expand=True)
        self.lst_assets.bind("<ButtonRelease-1>", self.on_click)

        self.refresh()

    def setBalances(self, AssetList):
        # AssetList is a list of bitshares.amount.Amount
        self.Balances = AssetList
        self.refresh()
        self.lst_assets.update()

    def refresh(self):
        self.lst_assets.delete(0, tk.END)
        for item in self.Balances:
            self.lst_assets.insert(tk.END, str(item))

    def on_click(self, *args):
        try:
            idx = self.lst_assets.index(self.lst_assets.curselection())
            self.asset_text_var.set(self.Balances[idx].symbol)
        except Exception:
            pass

class HistoryListFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.tx_json_tkvar = kwargs.pop('jsonvar', None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        self.HistItems = []
        self.accountId = ""

        self.lst_assets = ScrolledListbox(self)
        self.lst_assets.pack(padx=2, pady=2, side="top", fill="both", expand=True)

        button_frame = ttk.Frame(self)
        button_frame.pack(expand=False, fill="x", side="top")

        button_rawtx = ttk.Button(button_frame, text="Tx JSON", width=10, command=self.on_click_rawtx)
        button_rawtx.pack(side="left", fill="x", expand=True)
        button_explore = ttk.Button(button_frame, text="Block Explorer", command=self.on_click_explore)
        button_explore.pack(side="left", fill="x", expand=True)

        self.refresh()

    def setHistory(self, HistList, accountId):
        # HistList is an iterator over dict objects containing the operation wrapped in metadata
        self.HistItems = []        # Let's make it into a proper list though.
        self.accountId = accountId # Used to determine if history items are to/from
        for item in HistList:
            self.HistItems.append(item)
        self.refresh()

    def refresh(self):
        self.lst_assets.delete(0, tk.END)
        count = 0
        for item in self.HistItems:
            resolve_time = (count < 3) # Limit how many we get full date for (API call.. slow)
            self.lst_assets.insert(tk.END, pprintHistoryItem(item, self.accountId, resolve_time=resolve_time))
            count+=1

    def on_click_rawtx(self, *args):
        idx = self.lst_assets.index(self.lst_assets.curselection())
        Logger.Clear()
        Logger.Write("Retrieving transaction from block %d..."%self.HistItems[idx]["block_num"])
        try:
            trx = getTransactionFromHistoryItem(self.HistItems[idx])
            self.tx_json_tkvar.set(json.dumps(trx))
            Logger.Write("Transaction JSON is in 'Raw Transactions' tab.")
        except Exception as e:
            Logger.Write("Error occurred: %s"%str(e))
            pass
        Logger.Write("READY.")

    def on_click_explore(self, *args):
        try:
            idx = self.lst_assets.index(self.lst_assets.curselection())
            webbrowser.open("https://bitshares-explorer.io/#/operations/%s"%self.HistItems[idx]['id'])
        except Exception:
            pass

class TransferOpFrame(ttk.Frame):
    """
    Allows user to create, sign, and broadcast a Transfer operation.
    """

    def __init__(self, parent, *args, **kwargs):
        self.send_command = kwargs.pop("command", lambda *args, **kwargs: None)
        self.asset_text_var = kwargs.pop("assettextvariable", None)
        self.sender_text_var = kwargs.pop("sendernamevariable", None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)
        label_args = {"font": ("Helvetica", 16)}  # (Larger font spec for field labels.)
        ttk.Label(
            self,
            justify="left",
            text=(
                "\n1. Check sender's account name and SLIP48 path of signing key above."
                + "\n2. Set recipient's account name, amount, and asset symbol below."
                + "\n3. Click 'Send Transfer' to sign and broadcast to the network.\n"
            ),
        ).grid(row=1, column=1, columnspan=4)

        ##
        ## Sender Account: (Read-Only)
        ##

        ttk.Label(
            self, text="Send From: ", anchor="e", width=10, **label_args
        ).grid(
            row=2, column=1, padx=(8,2)
        )
        self.box_sender_name = ttk.Entry(
            self, textvariable=self.sender_text_var, justify="center", state="disabled",
        )
        self.box_sender_name.grid(row=2, column=2)
        self.sender_text_var.trace("w", self.any_field_on_change)

        ##
        ## Destination Account:
        ##

        ttk.Label(
            self, text="Send To: ", anchor="e", width=10, **label_args
        ).grid(
            row=3, column=1
        )
        self.recipient_text_var = tk.StringVar(value="")
        self.to_account_name = ttk.Entry(
            self, textvariable=self.recipient_text_var, justify="center"
        )
        self.to_account_name.grid(row=3, column=2, pady=12)
        self.to_account_name.bind("<FocusOut>", self.recipient_focus_out)
        self.recipient_text_var.trace("w", self.any_field_on_change)

        ##
        ## Amount and Asset:
        ##

        ttk.Label(
            self, text="Amount: ", anchor="e", width=10, **label_args
        ).grid(
            row=4, column=1
        )
        self.amount_text_var = tk.StringVar(value="0")
        self.box_amount_to_send = ttk.Entry(
            self, textvariable=self.amount_text_var, justify="right"
        )
        self.box_amount_to_send.grid(row=4, column=2)
        self.box_amount_to_send.bind("<FocusOut>", self.amount_focus_out)
        self.amount_text_var.trace("w", self.any_field_on_change)
        ttk.Label(
            self, text=" Asset: ", anchor="e", width=8, **label_args
        ).grid(
            row=4, column=3
        )
        self.box_asset_to_send = ttk.Entry(self, textvariable=self.asset_text_var)
        self.box_asset_to_send.grid(row=4, column=4)
        self.box_asset_to_send.bind("<FocusOut>", self.symbol_focus_out)
        self.asset_text_var.trace("w", self.any_field_on_change)
        # TODO: cache external call for LTM status and fee schedule
        ttk.Label(
            self,
            text="\nThis transaction will incur a small transaction fee in BTS,"
            + "\nas required by the network fee schedule.\n",
            font="-slant italic",
            justify="center",
        ).grid(
            row=6, column=1, columnspan=4
        )

        ##
        ## The Send Button:
        ##

        self.button_send = ttk.Button(
            self,
            text="Send Transfer",
            state="disabled",
            command=self.button_send_handler,
        )
        self.button_send.grid(row=7, column=1, columnspan=4)

    def any_field_on_change(self, *args):
        self.enable_send_if_all_fields_valid()

    def recipient_focus_out(self, *args):
        recipient_str = self.recipient_text_var.get().strip().lower()
        self.recipient_text_var.set(recipient_str)

    def symbol_focus_out(self, *args):
        symbol = self.asset_text_var.get().strip().upper()
        self.asset_text_var.set(symbol)

    def amount_focus_out(self, *args):
        amount_str = self.amount_text_var.get().strip()
        self.amount_text_var.set(amount_str)

    def sender_is_validatable(self):
        sender_str = self.sender_text_var.get().strip().lower()
        return is_valid_account_name(sender_str)

    def recipient_is_validatable(self):
        recipient_str = self.recipient_text_var.get().strip().lower()
        return is_valid_account_name(recipient_str)

    def symbol_is_validatable(self):
        symbol = self.asset_text_var.get().strip().upper()
        if len(symbol) == 0:
            return False
        ok = "QWERTYUIOPASDFGHJKLZXCVBNM0123456789."
        if not all(c in ok for c in symbol):
            return False
        return True

    def amount_is_validatable(self):
        amount_str = self.amount_text_var.get().strip()
        ok = "0123456789."
        if not all(c in ok for c in amount_str):
            return False
        try:
            return float(amount_str) > 0
        except ValueError:
            return False

    def enable_send_if_all_fields_valid(self):
        if (
                self.symbol_is_validatable() and
                self.amount_is_validatable() and
                self.sender_is_validatable() and
                self.recipient_is_validatable()
        ):
            self.button_send.configure(state="normal")
        else:
            self.button_send.configure(state="disabled")

    def button_send_handler(self):
        self.button_send.configure(state="disabled")
        Logger.Clear()
        try:
            account_name = self.to_account_name.get()
            asset_symbol = self.box_asset_to_send.get()
            amount_str = self.box_amount_to_send.get()
            if len(account_name) == 0:
                Logger.Write("Please provide an account name to send to!")
                return
            if len(asset_symbol) == 0:
                Logger.Write("Please specify asset to send!")
                return
            if len(amount_str) == 0:
                Logger.Write("Please specify amount to send!")
                return
            self.send_command(account_name, float(amount_str), asset_symbol)
        except ValueError as e:
            Logger.Write("ValueError: %s"%str(e))
        finally:
            self.button_send.update() # Eat any clicks that occured while disabled
            self.button_send.configure(state="normal") # Return to enabled state
            Logger.Write("READY.")


class ActivityMessageFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        log_frame = ttk.Frame(self, relief="groove", borderwidth=2)
        log_frame.pack(expand=True, fill="both")
        self.messages = tk.Message(log_frame, text="",
                                   width=640, background="light gray",
                                   anchor="n", pady=8, font="fixed")
        self.messages.pack(expand=True, fill="both")


class QueryPublicKeysFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.lookup_command = kwargs.pop('lookupcommand', lambda *args, **kwargs: None)
        self.textvariable_path = kwargs.pop('textvar_bip32_path', None)
        self.textvariable_key = kwargs.pop('textvar_bip32_key', None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        self.ownerPaths = ["48'/1'/0'/0'/0'","48'/1'/0'/0'/1'","48'/1'/0'/0'/2'","48'/1'/0'/0'/3'","48'/1'/0'/0'/4'"]
        self.activePaths = ["48'/1'/1'/0'/0'","48'/1'/1'/0'/1'","48'/1'/1'/0'/2'","48'/1'/1'/0'/3'","48'/1'/1'/0'/4'"]
        self.memoPaths = ["48'/1'/3'/0'/0'","48'/1'/3'/0'/1'","48'/1'/3'/0'/2'","48'/1'/3'/0'/3'","48'/1'/3'/0'/4'"]
        self.ownerKeys = []
        self.activeKeys = []
        self.memoKeys = []

        self.accountIndex_var = tk.StringVar(self, value = "0'")

        ##
        ## Upper Spacer:
        ##

        lblSLIPInfo = ttk.Label(self, text="SLIP-0048 schema:  48' / 1' / role' / account-index' / key-index'")
        lblSLIPInfo.pack(padx=10, pady=(10,6), expand=True, fill="x")

        frameAccountIndex = ttk.Frame(self)
        frameAccountIndex.pack(padx=10, expand=True, fill="x")
        labelAccountIndex = ttk.Label(frameAccountIndex, text="account-index: ")
        labelAccountIndex.pack(side="left")
        self.boxAccountIndex = ttk.Entry(frameAccountIndex, textvariable=self.accountIndex_var, width=8, state="disabled")
        self.boxAccountIndex.pack(side="left")

        lblRolesAndKeys = ttk.Label(self, text="Roles and Keys: The following keys are available on your Nano.")
        lblRolesAndKeys.pack(padx=10, pady=(6,0), expand=True, fill="x")
        lblRolesAndKeys2 = ttk.Label(self, text="To sign transactions, select a key that is authorized for your account:")
        lblRolesAndKeys2.pack(padx=10, pady=(0,4), expand=True, fill="x")

        ##
        ##  Lists:
        ##

        frameListGroup = ttk.Frame(self)
        frameListGroup.pack(padx=10, pady=5, fill="x")

        frameOwnerKeys = ttk.LabelFrame(frameListGroup, text = "Owner role:", borderwidth=0)
        frameOwnerKeys.pack(expand=True, fill="both", side="left")

        frameActiveKeys = ttk.LabelFrame(frameListGroup, text = "Active role:", borderwidth=0)
        frameActiveKeys.pack(expand=True, fill="both", side="left", padx=8)

        frameMemoKeys = ttk.LabelFrame(frameListGroup, text = "Memo role:", borderwidth=0)
        frameMemoKeys.pack(expand=True, fill="both", side="left")

        self.listOwnerKeys = ScrolledListbox(frameOwnerKeys, height=8, width=6)
        self.listOwnerKeys.pack(expand=True, fill="both")
        self.listOwnerKeys.bind("<ButtonRelease-1>", self.on_click_owners)

        self.listActiveKeys = ScrolledListbox(frameActiveKeys, height=8, width=6)
        self.listActiveKeys.pack(expand=True, fill="both")
        self.listActiveKeys.bind("<ButtonRelease-1>", self.on_click_actives)

        self.listMemoKeys = ScrolledListbox(frameMemoKeys, height=8, width=6)
        self.listMemoKeys.pack(expand=True, fill="both")
        self.listMemoKeys.bind("<ButtonRelease-1>", self.on_click_memos)

        ##
        ## Buttons:
        ##

        frameButtons = ttk.Frame(self)
        frameButtons.pack(pady=(4,8), side="right")

        self.button_get_addrs = ttk.Button(frameButtons, text="Query Addresses",
                                     command=lambda: self.on_click_get_addrs()
        )
        self.button_get_addrs.pack(side="left")

        self.button_confirm_addr = ttk.Button(frameButtons, text="Confirm Address",
                                     command=lambda: self.on_click_confirm_addr()
        )
        self.button_confirm_addr.pack(padx=(12,28), side="left")

        ##

        self.refresh()

    def refresh(self):
        self.refresh_keylistbox(self.listOwnerKeys, self.ownerPaths, self.ownerKeys)
        self.refresh_keylistbox(self.listActiveKeys, self.activePaths, self.activeKeys)
        self.refresh_keylistbox(self.listMemoKeys, self.memoPaths, self.memoKeys)

    def refresh_keylistbox(self, listbox, paths, keys):
        listbox.delete(0,tk.END)
        for idx in range(len(paths)):
            itemtext = "%s (%s)" % (paths[idx], keys[idx] if idx < len(keys) else "??")
            listbox.insert(tk.END, itemtext)
        listbox.insert(tk.END, "...")

    def clear_keys(self):
        self.ownerKeys = []
        self.activeKeys = []
        self.memoKeys = []
        self.refresh()

    def on_click_get_addrs(self):

        self.button_get_addrs.configure(state="disabled")
        Logger.Clear()
        try:
            self.lookup_handler()
        finally:
            self.button_get_addrs.update() # Eat any clicks that occured while disabled
            self.button_get_addrs.configure(state="normal") # Return to enabled state
            Logger.Write("READY.")

    def on_click_confirm_addr(self):

        self.button_confirm_addr.configure(state="disabled")
        Logger.Clear()
        try:
            self.address_confirm_handler()
        finally:
            self.button_confirm_addr.update() # Eat any clicks that occured while disabled
            self.button_confirm_addr.configure(state="normal") # Return to enabled state
            Logger.Write("READY.")

    def lookup_handler(self):

        self.clear_keys()

        # Owner Keys:
        Logger.Write("Querying Owner key paths from Nano...")
        self.ownerKeys = self.lookup_command(self.ownerPaths, False)
        self.refresh_keylistbox(self.listOwnerKeys, self.ownerPaths, self.ownerKeys)
        self.listOwnerKeys.update()
        if len(self.ownerKeys) < len(self.ownerPaths): return

        # Active Keys:
        Logger.Write("Querying Active key paths from Nano...")
        self.activeKeys = self.lookup_command(self.activePaths, False)
        self.refresh_keylistbox(self.listActiveKeys, self.activePaths, self.activeKeys)
        self.listActiveKeys.update()
        if len(self.activeKeys) < len(self.activePaths): return

        # Memo Keys:
        Logger.Write("Querying Memo key paths from Nano...")
        self.memoKeys = self.lookup_command(self.memoPaths, False)
        self.refresh_keylistbox(self.listMemoKeys, self.memoPaths, self.memoKeys)
        self.listMemoKeys.update()

    def address_confirm_handler(self):
        path = self.textvariable_path.get()
        Logger.Write("Confirming public key for path %s..."%path)
        try:
            address = self.lookup_command([path], False)[0]
            self.textvariable_key.set(address)
            Logger.Write("I retrieve key: %s" % address)
            Logger.Write("Please confirm that this matches the key shown on device...")
            self.lookup_command([path], True)
        except:
            self.textvariable_key.set("")
            Logger.Write("Could not confirm public key on device. Do not trust unconfirmed keys.")

    def on_click_keylistbox(self, listbox, paths, keys):
        idx = listbox.index(listbox.curselection())
        if idx < len(paths):
            self.textvariable_path.set(paths[idx])
            if idx < len(keys):
                self.textvariable_key.set(keys[idx])
            else:
                self.textvariable_key.set("")

    def on_click_owners(self, *args):
        self.on_click_keylistbox(self.listOwnerKeys, self.ownerPaths, self.ownerKeys)

    def on_click_actives(self, *args):
        self.on_click_keylistbox(self.listActiveKeys, self.activePaths, self.activeKeys)

    def on_click_memos(self, *args):
        self.on_click_keylistbox(self.listMemoKeys, self.memoPaths, self.memoKeys)


class RawTransactionsFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.serialize_command = kwargs.pop('serializecommand', lambda *args, **kwargs: None)
        self.sign_command = kwargs.pop('signcommand', lambda *args, **kwargs: None)
        self.broadcast_command = kwargs.pop('broadcastcommand', lambda *args, **kwargs: None)
        self.tx_json_tkvar = kwargs.pop('jsonvar', None)
        self.tx_serial_tkvar = kwargs.pop('serialvar', None)
        self.tx_signature_tkvar = kwargs.pop('signaturevar', None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        ##
        ## JSON Tx Panel
        ##

        frame_tx_json = ttk.LabelFrame(self, text = "1. Paste transaction JSON here:")
        frame_tx_json.pack(padx=6, pady=(8,4), expand=True, fill="both")

        self.entryTxJSON = ScrolledTextVarBound(frame_tx_json, height=6, textvariable=self.tx_json_tkvar)
        self.entryTxJSON.pack(expand=True, fill="both")

        self.tx_json_tkvar.trace("w", self.tx_json_changed)

        ##
        ## Serialized Tx Panel
        ##

        frame_tx_serial = ttk.LabelFrame(self, text = "2. Click \"Serialize\" to get APDU bytes for Nano to sign:")
        frame_tx_serial.pack(padx=6, pady=4, expand=True, fill="both")

        self.entryTxSerial = ScrolledTextVarBound(frame_tx_serial, height=4, textvariable=self.tx_serial_tkvar)
        self.entryTxSerial.pack(expand=True, fill="both")
        self.entryTxSerial.defaultFgColor = self.entryTxSerial.cget("fg")
        self.entryTxSerial.tag_configure("tlvtag", background="lightgray")
        self.entryTxSerial.tag_configure("tlvlen", background="lightgray")
        self.entryTxSerial.tag_configure("chainid", background="cyan")
        self.entryTxSerial.tag_configure("txfield", background="yellow")
        self.entryTxSerial.tag_configure("opid", background="lightgreen")
        self.entryTxSerial.tag_configure("opdata", background="lightgreen")
        self.entryTxSerial.tag_raise("sel")

        self.tx_serial_tkvar.trace("w", self.tx_serial_changed)

        ##
        ## Signature Panel
        ##

        frame_tx_signature = ttk.LabelFrame(self, text = "3. Click \"Sign\" to get signature from Nano. Then click \"Broadcast\" when ready to send:")
        frame_tx_signature.pack(padx=6, pady=4, expand=True, fill="both")

        self.entryTxSig = ScrolledTextVarBound(frame_tx_signature, height=2, textvariable=self.tx_signature_tkvar)
        self.entryTxSig.pack(expand=True, fill="both")
        self.entryTxSig.defaultFgColor = self.entryTxSig.cget("fg")

        self.tx_signature_tkvar.trace("w", self.tx_sig_changed)

        ##
        ## Buttons:
        ##

        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=(4,8))

        self.var_colorize = tk.IntVar(value=1)
        self.chkColorize = ttk.Checkbutton(buttons_frame, text="Colorize Serial",
                                           variable=self.var_colorize, command=lambda: self.colorize_check_handler())
        self.chkColorize.pack(padx=4, side="left")

        self.btnSerialize = ttk.Button(buttons_frame, text="1. Serialize",
                                       command=lambda: self.serialize_handler())
        self.btnSerialize.pack(padx=4, side="left")

        self.btnSign = ttk.Button(buttons_frame, text="2. Sign",
                                  command=lambda: self.sign_handler(),
                                  state="disabled")
        self.btnSign.pack(padx=4, side="left")

        self.btnBroadcast = ttk.Button(buttons_frame, text="3. Broadcast",
                                       command=lambda: self.broadcast_handler(),
                                       state="disabled")
        self.btnBroadcast.pack(padx=4, side="left")


    def tx_json_changed(self, *args):
        self.entryTxSerial.config(fg="gray")
        self.btnSign.configure(state="disabled")
        self.btnBroadcast.configure(state="disabled")
        # ^
        # Twiddle foreground colors of entryTxSerial to indicate correspondence
        # to current contents of entryTxJSON.
        # v
    def tx_serial_changed(self, *args):
        self.entryTxSerial.config(fg=self.entryTxSerial.defaultFgColor)
        self.entryTxSig.config(fg="gray")
        self.btnSign.configure(state="normal")
        self.btnBroadcast.configure(state="disabled")
        # ^
        # v
    def tx_sig_changed(self, *args):
        self.entryTxSig.config(fg=self.entryTxSig.defaultFgColor)
        possible_hex = self.tx_signature_tkvar.get().strip()
        try:
            binascii.unhexlify(possible_hex) # raise if not valid hex
            valid_hex = True
        except:
            valid_hex = False
        if valid_hex and len(possible_hex) > 0:
            self.btnBroadcast.update() # Eat any clicks queued while disabled
            self.btnBroadcast.configure(state="normal")
        else:
            self.btnBroadcast.configure(state="disabled")

    def colorize_check_handler(self):
        self.colorizeSerialHex(self.entryTxSerial)

    def serialize_handler(self):
        self.btnSerialize.configure(state="disabled")
        Logger.Clear()
        Logger.Write("Attempting to serialize JSON transaction...")
        try:
            self.serialize_command()
        except:
            pass
        self.colorizeSerialHex(self.entryTxSerial)
        self.btnSerialize.update()
        self.btnSerialize.configure(state="normal")
        Logger.Write("READY.")

    def sign_handler(self):
        self.btnSign.configure(state="disabled")
        self.btnBroadcast.configure(state="disabled")
        Logger.Clear()
        Logger.Write("Asking Nano to sign serialized transaction...")
        try:
            self.sign_command()
            Logger.Write("Received signature from Nano.  Click \"Broadcast\" when ready to transmit.")
        except:
            pass
        self.btnSign.update() # Eat any clicks that occured while disabled.
        self.btnSign.configure(state="normal")
        Logger.Write("READY.")

    def broadcast_handler(self):
        self.btnBroadcast.configure(state="disabled")
        Logger.Clear()
        try:
            self.broadcast_command()
        except:
            pass
        self.btnBroadcast.update() # Eat any clicks queued while disabled
        self.btnBroadcast.configure(state="normal")
        Logger.Write("READY.")

    def colorizeSerialHex(self, w):
        for tag in w.tag_names():
            w.tag_remove(tag, "1.0", tk.END)
        if self.var_colorize.get() != 1:
            return
        try:
            tindex = w.index("1.0 + 0c")
            # ChainID
            tindex = self.applyTlvTagColor(w, tindex, "chainid")
            # Ref block, num, and expiration:
            tindex = self.applyTlvTagColor(w, tindex, "txfield")
            tindex = self.applyTlvTagColor(w, tindex, "txfield")
            tindex = self.applyTlvTagColor(w, tindex, "txfield")
            # Num operations:
            tindex = self.applyTlvTagColor(w, tindex, "txfield")
            numOps = int.from_bytes(binascii.unhexlify("".join(w.lastHexField.split())), byteorder="big", signed=False)
            # Operations:
            while numOps > 0:
                numOps -= 1
                tindex = self.applyTlvTagColor(w, tindex, "opid")
                tindex = self.applyTlvTagColor(w, tindex, "opdata")
            # Tx Extensions
            tindex = self.applyTlvTagColor(w, tindex, "txfield")
        except:
            pass

    def applyTlvTagColor(self, w, tindex, tagname):

        def getHexBytes(tindex, numbytes):
            charbuf = ""
            nibblecount = 0
            charcount = 0
            char = ''
            while nibblecount < (2*numbytes):
                char = w.get(tindex+"+%dc"%charcount, tindex+"+%dc"%(1+charcount))
                if len(char) == 0:
                    raise Exception("Hex stream ended before N bytes read.")
                if len(char) != 1:
                    raise Exception("Hex stream unexpected char string read.")
                charcount += 1
                if char.isspace():
                    charbuf += char
                    continue
                if char in '0123456789abcdefABCDEF':
                    nibblecount +=1
                    charbuf += char
                    continue
                raise Exception("Unparsible Hex character.")
            return charbuf

        tindex0 = tindex
        tagHex = getHexBytes(tindex0, 1)
        tagByte = binascii.unhexlify("".join(tagHex.split()))
        if tagByte!=b'\x04':
            raise Exception()
        tindex1 = w.index(tindex0+"+%dc"%(len(tagHex)))

        tagLenHex = getHexBytes(tindex1, 1) # TODO: Is a varint so could be >1 bytes
        tagLen = int.from_bytes(binascii.unhexlify("".join(tagLenHex.split())), byteorder="big", signed=False)
        tindex2 = w.index(tindex1+"+%dc"%(len(tagLenHex)))

        if tagLen > 0:
            fieldHex = getHexBytes(tindex2, tagLen)
            tindex3 = w.index(tindex2 + "+%dc"%(len(fieldHex)))
            w.lastHexField = fieldHex  # Stash this value somewhere it can be found
        else:
            tindex3 = tindex2
            w.lastHexField = ""

        # TODO: when applying tags avoid leading/trailing whitespace

        w.tag_add("tlvtag", tindex0, tindex1)
        w.tag_add("tlvlen", tindex1, tindex2)
        if tagLen > 0:
            w.tag_add(tagname, tindex2, tindex3)

        return tindex3

class AboutFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.txtvar_api_node = kwargs.pop('txtvar_api_node', None)
        ttk.Frame.__init__(self, parent, *args, **kwargs)

        ##
        ## Upper Spacer:
        ##

        lblSpacerActiveTop = ttk.Label(self, text="")
        lblSpacerActiveTop.pack(expand=True, fill="y")

        ##
        ## App Version
        ##

        labelAppVersion = ttk.Label(self, text="SimpleGUIWallet, version "+version.VERSION, font=("fixed", 18),)
        labelAppVersion.pack(pady=4)

        ## Node URL:

        self.node_url_msg = tk.StringVar()
        self.node_url_msg.set("No API node connection")
        ttk.Label(self, textvariable=self.node_url_msg).pack(pady=6)

        ## App Description:

        labelAppDescription = tk.Message(self, width=420, anchor="n", justify="center",
                                         background = ttk.Style().lookup("TFrame", "background"),
                                         text = "" +
            "A very simple wallet for BitShares. No private or public keys are stored by this app. " +
            "Transactions are sent to Ledger Nano S device for signing, and then broadcast to network.\n\n" +
            "Specify your own account name above.  View account assets at left.  Use the tabs in this widget " +
            "for various operations (e.g. Transfer), or to browse public keys managed by your Ledger device.  " +
            "Your account will need a key from the device listed in its \"authorities\" before you can sign transactions.")
        labelAppDescription.pack(expand=True, fill="x")

        ## Tutorial Link:

        labelAppTutorial = ttk.Label(self, text="A tutorial is available at https://docs.bitshares.eu/",
                                     foreground="blue", font=("fixed","14", "italic"), cursor="hand2")
        labelAppTutorial.pack(pady=4)
        labelAppTutorial.bind("<ButtonRelease-1>", self.on_click_tutorial)

        ## Lower Spacer:

        lblSpacerActiveBottom = ttk.Label(self, text="")
        lblSpacerActiveBottom.pack(expand=True, fill="y")

        ## Behaviors:

        self.bind("<FocusIn>", self.on_tab_focus)


    def on_tab_focus(self, *args):
        self.node_url_msg.set("Using API Node:  " + self.txtvar_api_node.get())

    def on_click_tutorial(self, *args):
        try:
            webbrowser.open("https://docs.bitshares.eu/en/master/user_guide/ledger_nano.html")
        except Exception:
            pass

