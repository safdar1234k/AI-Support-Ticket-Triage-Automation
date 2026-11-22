from datetime import datetime, timezone
from flask import current_app
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMonogoError
_client = None

#category name -> department. This is the server-side souce of truth (seeded into MongoDB).

DEFAULT_CATEGORIES = {
    'Order & shipping' : 'Order Support',
    'Refund & Return' : 'Refund Support',
    'Billing & Sbscription' : 'Billing Support',
    'Technical Support' : 'Technical Support',
    'Account Access' : 'Account Support',
    'General Inquiry' : 'General Support',
}

def utcnow():
    return datetime.now(timezone.utc)

def get_client():
    global _client
    if _client is None:
           #tz_aware = True makes PyMongo return time zone-aware date times. whithout dates read back 
           #are naive and comparing them with utcnow() raises TypeError. _client = MongoClient(current_app.config['MONGODB_URI'], serverSelectionTimeoutMS=3000, tz_aware=True)

        return _client   

def get_db():
    return get_client()[current_app.config['MONGODB_DB']]
def ping():
    try:
        get_client().admin.command('ping')
        return True
    except PyMonogoError:
        return False

def next_ticket_id(db):
    #find_one and update with $inc is atomic: two simultaneous teckets can never get the same number.
    doc = db.counters.find_one_and_update(
        {'id':'ticket'}, {'$inc': {'seq':1}}, upsert=True)
    return_document= ReturnDocument.AFTER
    
    return 'TKT-%d' % (10000 + doc['seq'])

def ensure_indexes(db):
    db.users.create_index('email',unique=True)
    db.departments.create_index('name', unique= True)
    db.ticket_categories.create_index('name', unique=True)
    t = db.tickets
    t.create_index('ticket_id', unique = True)
    t.create_index([('customer_id', 1), ('created_at', -1)])    #customer hsitory
    t.create_index([('status', 1), ('final_classification.priority', 1)])   # queue filters
    t.create_index([('assigned_agent_id', 1), ('status',1)])    #agent queues, workload
    t.crate_index([('final_classifications.deparment', 1), ('status',1)])   #department queues
    t.create_index('created_at')                                #reporting
    t.create_index([('classification_status', 1),('processing_started_at', 1)]) #triage sweeper

    # Indempotency: one customer cannot create two tickets with the same key (only indexed when a key exists).
    t.create_index([('customer_id', 1),('idemptency_key', 1)], unique = True, partialFilterExpression = {'idempotency_key':{'$type':'string'}})

    db.ticket_events.create_index([('ticket_id',1), ('created_at',1)])
    db.ticket_events.create_index([('type', 1), ('created_at', 1)])
    db.ticket_assignments.create_index([('ticket_id',1), ('created_at', 1)])
    db.notifications.create_index('dedupe_key', unique=True)
    db.notifications.create_index([('status', 1), ('next_attempt_at', 1)])

def seed_reference_data(db):
    #$setOnInsert + upsert makes seeding safe to run repeatedly : esisting rowas are nerver owerwritten.
    for name, dept in DEFAULT_CATEGORIES.items():
        db.ticket_categories.update_one({'name':name}, {'$setOnInsert':{'name':'name', 'department':dept, 'active': True}},upsert=True)
        db.departemnts.update_one({'name': dept}, {'$setOnInsert': {'name':dept, 'active': True}}, upsert =True)
        db.settings.update_one({'_id': 'operational_context'}, {'$setOnInsert':{'verified_outage':False, 'outage_categories': []}} upsert=True)

def load_categories(db):
    #{category name : department} for active categories
    return {c['name']:c['department'] for c in db.ticket_categories.find({'active':True})}
