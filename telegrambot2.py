import asyncio
import logging
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackContext

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token (replace with your actual bot token)
TOKEN = '6796101410:AAEEUbVjCcwBFsXex6PlfYg4rdRhoz0Rs98'

# Define states for the conversation flow
MENU, ADD_NOTE, QUANTITY, NAME, ADDRESS, PHONE, CONFIRMATION = range(7)

# Define the menu with prices, image paths, and descriptions
menu = {
    "Plat 01 (300DZD)": {"price": 300, "image": 'https://imgur.com/YcG0Ayj', "description": "Description du plat 01"},
    "Plat 02 (350DZD)": {"price": 350, "image": 'https://imgur.com/RiQQ6c4', "description": "Description du plat 02"},
    "Plat 03 (350DZD)": {"price": 350, "image": 'https://imgur.com/tQgPD5K', "description": "Description du plat 03"},
    "Plat 04 (400DZD)": {"price": 400, "image": 'https://imgur.com/tVJKmCZ', "description": "Description du plat 04"},
    "Plat 05 (450DZD)": {"price": 450, "image": 'https://imgur.com/iw4jmkJ', "description": "Description du plat 05"},
    "Plat 06 (500DZD)": {"price": 500, "image": 'https://imgur.com/KVM0Ow0', "description": "Description du plat 06"},
    "Jus Citron Carott Banane (150DZD)": {"price": 150, "image": 'https://imgur.com/I4bpC9m', "description": "Description du jus 01"},
    "Jus Mokhito (120DZD)": {"price": 120, "image": 'https://imgur.com/SFj1e6r', "description": "Description du jus 02"},
    "Muffins au chocolat (80DZD)": {"price": 80, "image": 'https://imgur.com/SEaqiFH', "description": "Description du snack"},
    "Muffins au Confiture (80DZD)": {"price": 80, "image": 'https://imgur.com/ol2c6gm', "description": "Description du snack"},
}

# Define the chef's chat ID
CHEF_CHAT_ID = ['1849539271', '5015099173']  # Replace with the actual chat ID of the chef

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command by sending a welcome message."""
    logger.info("Start command received")
    await update.message.reply_text('Bienvenue sur notre bot de fresco food ! Pour passer une commande, utilisez la commande /menu.')

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the menu as an album of images."""
    logger.info("Showing menu")
    chat_id = update.effective_chat.id
    media_group = []
    for item, details in menu.items():
        caption = f"{item} - DZD{details['price']}\n{details['description']}"
        try:
            media_group.append(InputMediaPhoto(media=details['image'], caption=caption))
        except FileNotFoundError:
            logger.error(f"Image file not found: {details['image']}")
            continue
    if media_group:
        await context.bot.send_media_group(chat_id=chat_id, media=media_group)
    else:
        await context.bot.send_message(chat_id=chat_id, text="Désolé, il y a eu un problème de chargement des images du menu.")

    buttons = [[InlineKeyboardButton(item, callback_data=item)] for item in menu.keys()]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=chat_id, text="Veuillez sélectionner un plat :", reply_markup=reply_markup)

    return MENU

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's selection from the menu."""
    query = update.callback_query
    await query.answer()
    selected_dish = query.data
    logger.info(f"User selected: {selected_dish}")

    context.user_data['selected_dish'] = selected_dish
    await query.edit_message_text(text=f"Combien de {selected_dish} souhaitez-vous commander ?")

    return QUANTITY

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's input for quantity."""
    try:
        quantity = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Veuillez entrer un nombre valide pour la quantité.")
        return QUANTITY

    selected_dish = context.user_data['selected_dish']
    logger.info(f"User selected quantity: {quantity} for dish: {selected_dish}")

    context.user_data.setdefault('plats_sélectionnés', []).append((selected_dish, quantity))
    context.user_data.setdefault('prix_total', 0)
    context.user_data['prix_total'] += menu[selected_dish]['price'] * quantity

    selected_items_text = "\n".join([f"{item} (x{qty})" for item, qty in context.user_data['plats_sélectionnés']])
    buttons = [
        [InlineKeyboardButton(f"Supprimer {item}", callback_data=f"remove_{item}")] for item, qty in context.user_data['plats_sélectionnés']
    ]
    buttons.append([InlineKeyboardButton("Finaliser la commande", callback_data='finalize')])
    buttons.append([InlineKeyboardButton("Ajouter un commentaire", callback_data='add_note')])
    buttons.append([InlineKeyboardButton("Ajouter plus de plats", callback_data='add_more')])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"Plats sélectionnés:\n{selected_items_text}\n\nTotal: DZD{context.user_data['prix_total']}\n\nVous pouvez choisir plus de plats, ajouter un commentaire, ou cliquer sur 'Finaliser la commande' pour compléter votre commande.",
        reply_markup=reply_markup
    )

    return ADD_NOTE

async def handle_remove_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the removal of a selected item."""
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Removing item: {data}")

    if data.startswith("remove_"):
        item_to_remove = data.replace("remove_", "")
        for i, (item, qty) in enumerate(context.user_data['plats_sélectionnés']):
            if item == item_to_remove:
                context.user_data['plats_sélectionnés'].pop(i)
                context.user_data['prix_total'] -= menu[item]['price'] * qty
                break

        selected_items_text = "\n".join([f"{item} (x{qty})" for item, qty in context.user_data['plats_sélectionnés']])
        buttons = [
            [InlineKeyboardButton(f"Supprimer {item}", callback_data=f"remove_{item}")] for item, qty in context.user_data['plats_sélectionnés']
        ]
        buttons.append([InlineKeyboardButton("Finaliser la commande", callback_data='finalize')])
        buttons.append([InlineKeyboardButton("Ajouter un commentaire", callback_data='add_note')])
        buttons.append([InlineKeyboardButton("Ajouter plus de plats", callback_data='add_more')])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(
            text=f"Plats mis à jour :\n{selected_items_text}\n\nTotal: DZD{context.user_data['prix_total']}\n\nVous pouvez choisir plus de plats, ajouter un commentaire, ou cliquer sur 'Finaliser la commande' pour compléter votre commande.",
            reply_markup=reply_markup
        )

    return ADD_NOTE

async def handle_add_note_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user to add a note."""
    query = update.callback_query
    await query.answer()
    logger.info("User requested to add a note")
    await query.edit_message_text(text="Vous pouvez ajouter un commentaire à votre commande maintenant. Tapez votre commentaire ci-dessous :")

    return ADD_NOTE

async def handle_add_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's input for adding a note."""
    user_note = update.message.text
    logger.info(f"User added note: {user_note}")
    context.user_data['note'] = user_note

    selected_items_text = "\n".join([f"{item} (x{qty})" for item, qty in context.user_data['plats_sélectionnés']])
    buttons = [
        [InlineKeyboardButton(f"Supprimer {item}", callback_data=f"remove_{item}")] for item, qty in context.user_data['plats_sélectionnés']
    ]
    buttons.append([InlineKeyboardButton("Finaliser la commande", callback_data='finalize')])
    buttons.append([InlineKeyboardButton("Ajouter un commentaire", callback_data='add_note')])
    buttons.append([InlineKeyboardButton("Ajouter plus de plats", callback_data='add_more')])
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"Plats sélectionnés :\n{selected_items_text}\n\nTotal : DZD{context.user_data['prix_total']}\n\nVous pouvez choisir plus de plats, ajouter un commentaire, ou cliquer sur 'Finaliser la commande' pour compléter votre commande.",
        reply_markup=reply_markup
    )

    return ADD_NOTE

async def handle_finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalize the order and send details to the chef."""
    query = update.callback_query
    await query.answer()
    logger.info("User finalized the order")

    selected_items_text = "\n".join([f"{item} (x{qty})" for item, qty in context.user_data['plats_sélectionnés']])
    total_price = context.user_data['prix_total']
    user_note = context.user_data.get('note', 'Aucun commentaire')
    user_id = update.effective_user.id

    order_summary = (
        f"Commande de l'utilisateur {user_id} :\n"
        f"{selected_items_text}\n"
        f"Total : DZD{total_price}\n"
        f"Commentaire : {user_note}"
    )

    for chef_id in CHEF_CHAT_ID:
        await context.bot.send_message(chat_id=chef_id, text=order_summary)

    await query.edit_message_text(text="Votre commande a été finalisée et envoyée au chef. Merci de votre commande !")

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END

async def handle_add_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the option to add more items to the order."""
    query = update.callback_query
    await query.answer()
    logger.info("User wants to add more items")

    await query.edit_message_text(text="Veuillez sélectionner un plat à ajouter à votre commande.")

    buttons = [[InlineKeyboardButton(item, callback_data=item)] for item in menu.keys()]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.reply_text("Sélectionnez un autre plat :", reply_markup=reply_markup)

    return MENU

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle any non-command messages."""
    await update.message.reply_text("Veuillez utiliser les commandes disponibles pour passer une commande.")

async def main() -> None:
    """Start the bot and handle updates."""
    application = ApplicationBuilder().token(TOKEN).build()

    # Define the conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('menu', show_menu)],
        states={
            MENU: [CallbackQueryHandler(handle_menu_selection)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)],
            ADD_NOTE: [CallbackQueryHandler(handle_remove_item, pattern='^remove_')],
            ADD_NOTE: [CallbackQueryHandler(handle_add_note_request, pattern='^add_note$')],
            ADD_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_note)],
            ADD_NOTE: [CallbackQueryHandler(handle_finalize_order, pattern='^finalize$')],
            ADD_NOTE: [CallbackQueryHandler(handle_add_more, pattern='^add_more$')],
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
    )

    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('menu', show_menu))

    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())

