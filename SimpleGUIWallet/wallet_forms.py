import tkinter as tk
import ttk
import Logger

class WhoAmIFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.button_command = kwargs.pop('command', lambda *args, **kwargs: None)
        self.textvariable = kwargs.pop('textvariable', None)
        self.textvariable_path = kwargs.pop('textvariablebip32', None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        frame_row_1 = ttk.Frame(self)
        frame_row_1.pack(fill="x")
        frame_row_2 = ttk.Frame(self)
        frame_row_2.pack(fill="x")

        lbl_from_account_name = ttk.Label(frame_row_1, text="BitShares User Account:",
                                         font=("Helvetica", 16), **common_args)
        lbl_from_account_name.pack(side="left")

        box_from_account_name = ttk.Entry(frame_row_1, width=30, textvariable=self.textvariable)
        box_from_account_name.pack(side="left", padx=10)

        self.button = ttk.Button(frame_row_1, text="Refresh Balances",
                                     command=lambda: self.button_handler())
        self.button.pack(side="left", padx=5)

        lbl_bip32_path = ttk.Label(frame_row_2, text="BIP32 Path:",
                                         font=("Helvetica", 16), **common_args)
        lbl_bip32_path.pack(side="left")

        box_bip32_path = ttk.Entry(frame_row_2, width=30, textvariable=self.textvariable_path)
        box_bip32_path.pack(side="left", padx=10)

    def button_handler(self):
        self.button.configure(state="disabled")
        Logger.Clear()
        try:
            account_name = self.textvariable.get()
            if len(account_name) == 0:
                Logger.Write("Please provide an account name!")
                return
            self.button_command(account_name)
        finally:
            self.button.update() # Eat any clicks that occured while disabled
            self.button.configure(state="normal") # Return to enabled state
            Logger.Write("READY.")


class AssetListFrame(ttk.LabelFrame):

    def __init__(self, parent, *args, **kwargs):

        self.asset_text_var = kwargs.pop('assettextvariable', None)

        ttk.LabelFrame.__init__(self, parent, *args, **kwargs)

        common_args={}

        self.Balances = ["One", "Two"]

        self.lst_assets = tk.Listbox(self, bd=0)
        self.lst_assets.pack(side="left", fill="y")
        self.lst_assets.bind("<ButtonRelease-1>", self.on_click)

        self.refresh()

    def setBalances(self, AssetList):
        self.Balances = AssetList
        self.refresh()

    def refresh(self):
        self.lst_assets.delete(0, tk.END)
        for item in self.Balances:
            self.lst_assets.insert(tk.END, str(item))

    def on_click(self, *args):
        try:
            idx = self.lst_assets.index(self.lst_assets.curselection())
            self.asset_text_var.set(self.Balances[idx].symbol)
        except:
            pass

class TransferOpFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.send_command = kwargs.pop('command', lambda *args, **kwargs: None)
        self.asset_text_var = kwargs.pop('assettextvariable', None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        ##
        ## Upper Spacer:
        ##

        lblSpacerActiveTop = ttk.Label(self, text="", **common_args)
        lblSpacerActiveTop.pack(expand=True, fill="y")

        ##
        ## Destination Account:
        ##

        frameToWhom = ttk.Frame(self, **common_args)
        frameToWhom.pack(padx=10, pady=5, fill="x")

        self.to_account_name = ttk.Entry(frameToWhom)
        self.to_account_name.pack(side="right", padx=10)

        labelSendTo = ttk.Label(frameToWhom, text="Send To: (BitShares User Account)",
                               font=("Helvetica", 16), **common_args)
        labelSendTo.pack(side="right")

        ##
        ## Amount and Asset:
        ##

        frameSendAmount = ttk.Frame(self, **common_args)
        frameSendAmount.pack(padx=10, pady=5, fill="x")

        self.box_asset_to_send = ttk.Entry(frameSendAmount, width=10, textvariable=self.asset_text_var)
        self.box_asset_to_send.pack(side="right", padx=10)

        labelAsset = ttk.Label(frameSendAmount, text="Asset:",
                           font=("Helvetica", 16), **common_args)
        labelAsset.pack(padx=(20,0),side="right")

        self.box_amount_to_send = ttk.Entry(frameSendAmount)
        self.box_amount_to_send.pack(side="right", padx=10)

        labelAmount = ttk.Label(frameSendAmount, text="Amount:",
                            font=("Helvetica", 16), **common_args)
        labelAmount.pack(side="right")

        ##
        ## The Send Button:
        ##
        self.button_send = ttk.Button(self, text="Send Transfer",
                                     command=lambda: self.button_send_handler()
        )
        self.button_send.pack(pady=30)

        ##
        ## Lower Spacer:
        ##

        lblSpacerActiveBottom = ttk.Label(self, text="", **common_args)
        lblSpacerActiveBottom.pack(expand=True, fill="y")

    def button_send_handler(self):
        self.button_send.configure(state="disabled")
        Logger.Clear()
        try:
            account_name = self.to_account_name.get()
            asset_symbol = self.box_asset_to_send.get()
            amount = self.box_amount_to_send.get()
            if len(account_name) == 0:
                Logger.Write("Please provide an account name to send to!")
                return
            if len(asset_symbol) == 0:
                Logger.Write("Please specify asset to send!")
                return
            if len(amount) == 0:
                Logger.Write("Please specify amount to send!")
                return
            self.send_command(account_name, amount, asset_symbol)
        finally:
            self.button_send.update() # Eat any clicks that occured while disabled
            self.button_send.configure(state="normal") # Return to enabled state
            Logger.Write("READY.")


class ActivityMessageFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        log_frame = ttk.LabelFrame(self, text="Activity", relief="groove",
                                  **common_args)
        log_frame.pack(expand=True, fill="both")
        self.messages = tk.Message(log_frame, text="",
                                   width=580, background="light gray",
                                   anchor="n", pady=8, font="fixed")
        self.messages.pack(expand=True, fill="both")


class QueryPublicKeysFrame(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):

        self.lookup_command = kwargs.pop('lookupcommand', lambda *args, **kwargs: None)

        ttk.Frame.__init__(self, parent, *args, **kwargs)

        common_args={}

        ##
        ## Upper Spacer:
        ##

        lblSpacerActiveTop = ttk.Label(self, text="", **common_args)
        lblSpacerActiveTop.pack(expand=True, fill="y")

        ##
        ##  Lists:
        ##

        frameListGroup = ttk.Frame(self, **common_args)
        frameListGroup.pack(padx=10, pady=5, fill="x")

        frameOwnerKeys = ttk.LabelFrame(frameListGroup, text = "Owner:")
        frameOwnerKeys.pack(expand=True, fill="both", side="left")

        frameActiveKeys = ttk.LabelFrame(frameListGroup, text = "Active:")
        frameActiveKeys.pack(expand=True, fill="both", side="left", padx=8)

        frameMemoKeys = ttk.LabelFrame(frameListGroup, text = "Memo:")
        frameMemoKeys.pack(expand=True, fill="both", side="left")

        self.listOwnerKeys = tk.Listbox(frameOwnerKeys)
        self.listOwnerKeys.pack(expand=True, fill="both")

        self.listActiveKeys = tk.Listbox(frameActiveKeys)
        self.listActiveKeys.pack(expand=True, fill="both")

        self.listMemoKeys = tk.Listbox(frameMemoKeys)
        self.listMemoKeys.pack(expand=True, fill="both")

        ##
        ## Buttons:
        ##

        self.button_get_addrs = ttk.Button(self, text="Query Addresses",
                                     command=lambda: self.lookup_handler()
        )
        self.button_get_addrs.pack(pady=(10,15))

    def lookup_handler(self):

        addresses = self.lookup_command("48'/1'/0'/0'/", 0, 3, True)
        self.listOwnerKeys.delete(0,tk.END)
        for item in addresses:
            self.listOwnerKeys.insert(tk.END, item)
        self.listOwnerKeys.insert(tk.END, "...")

        addresses = self.lookup_command("48'/1'/1'/0'/", 0, 3, True)
        self.listActiveKeys.delete(0,tk.END)
        for item in addresses:
            self.listActiveKeys.insert(tk.END, item)
        self.listActiveKeys.insert(tk.END, "...")

        addresses = self.lookup_command("48'/1'/3'/0'/", 0, 3, True)
        self.listMemoKeys.delete(0,tk.END)
        for item in addresses:
            self.listMemoKeys.insert(tk.END, item)
        self.listMemoKeys.insert(tk.END, "...")