import db_utils
import time # Just in case for any time-based debugging, though not strictly needed for FAQs

if __name__ == "__main__":
    print("--- Initializing DB (ensures tables exist) ---")
    # This will call create_conversations_table(), create_last_message_time_table(),
    # AND create_faqs_table() as per your db_utils.init_db()
    db_utils.init_db()

    print("\n--- Adding Sample FAQs ---")
    # We'll leave embedding as an empty string for now, as it's populated on Day 2
    faq_id_1 = db_utils.add_faq("What are your business hours?", "We are open Monday to Friday, 9 AM to 5 PM EAT.")
    faq_id_2 = db_utils.add_faq("How can I contact customer support?", "You can reach us via email at support@example.com or call us at +254 7XX YYY ZZZZ.")
    faq_id_3 = db_utils.add_faq("Do you offer refunds?", "Yes, we offer a full refund within 30 days of purchase with original receipt.")
    faq_id_4 = db_utils.add_faq("Where are you located?", "Our main office is in Nairobi, Kenya.")

    print("\n--- Getting All FAQs ---")
    all_faqs = db_utils.get_all_faqs()
    if all_faqs:
        for faq in all_faqs:
            # Print only relevant parts to keep output clean, embedding is empty anyway
            print(f"ID: {faq['id']}, Q: '{faq['question'][:70]}...', A: '{faq['answer'][:70]}...'")
    else:
        print("No FAQs found.")

    # Only attempt to delete if faq_id_2 was successfully added
    if faq_id_2 is not None:
        print(f"\n--- Deleting FAQ with ID {faq_id_2} (e.g., 'How can I contact...') ---")
        db_utils.delete_faq(faq_id_2)
    else:
        print("\n--- Skipping deletion as FAQ ID 2 was not added ---")


    print("\n--- Getting All FAQs After Deletion ---")
    all_faqs_after_delete = db_utils.get_all_faqs()
    if all_faqs_after_delete:
        for faq in all_faqs_after_delete:
            print(f"ID: {faq['id']}, Q: '{faq['question'][:70]}...'")
    else:
        print("No FAQs found after deletion.")


    print("\n--- Attempting to delete non-existent FAQ (ID 999) ---")
    db_utils.delete_faq(999) # ID that likely doesn't exist

    print("\n--- Manual FAQ Testing Script Complete ---")