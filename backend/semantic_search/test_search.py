
from search_engine import search_documents


# Test support ticket scenarios
test_tickets = [
    "My laptop cannot connect to the office Wi-Fi.",
    "I am not receiving new emails in Outlook.",
    "I forgot my password and cannot log in.",
    "My computer is running very slowly.",
    "My printer is not printing documents.",
    "My VPN connection is not working.",
    "My application keeps crashing.",
    "I cannot hear anything during online meetings."
]


def run_tests():

    print("=" * 60)
    print("SUPPORTPILOT - SEMANTIC SEARCH TESTING")
    print("=" * 60)

    for number, ticket in enumerate(test_tickets, start=1):

        print(f"\nTEST CASE {number}")
        print("-" * 60)

        print("Ticket:", ticket)

        results = search_documents(ticket, top_k=3)

        print("\nRetrieved Documents:")

        for rank, doc in enumerate(results, start=1):

            print(f"\nResult {rank}")
            print("Title:", doc["title"])
            print("Category:", doc["category"])
            print("Distance:", round(doc["distance"], 4))

    print("\n" + "=" * 60)
    print("ALL SEARCH TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
