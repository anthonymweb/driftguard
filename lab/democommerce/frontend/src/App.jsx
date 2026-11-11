import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, AudioLines, BadgeCheck, Check,
  CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, CircleUserRound, Clock3,
  CreditCard, Headphones, Heart, House, LampDesk, Leaf, LogIn, LogOut, Menu,
  Minus, Package, PackageCheck, Plus, Search, Settings2, ShieldCheck, ShoppingBag,
  SlidersHorizontal, Sparkles, Truck, UserRound, X,
} from 'lucide-react';

const API = (import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://127.0.0.1:8001' : '')).replace(/\/$/, '');
const CATEGORIES = ['All', 'Audio', 'Home', 'Carry', 'Desk', 'Outdoor'];

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: 'include', ...options,
    headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(data.detail || 'Something went wrong. Please try again.'), { status: response.status });
  return data;
}

const money = (cents = 0) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(cents / 100);
const itemCount = (cart) => cart?.item_count || 0;

function ProductArt({ category, large = false }) {
  const icons = { Audio: Headphones, Home: House, Carry: Package, Desk: LampDesk, Outdoor: Leaf };
  const Icon = icons[category] || Package;
  return <div className={`product-art art-${category?.toLowerCase()} ${large ? 'art-large' : ''}`} aria-hidden="true"><span className="art-orbit orbit-one"/><span className="art-orbit orbit-two"/><div className="art-object"><Icon strokeWidth={1.05}/></div><span className="art-caption">DC / OBJECTS</span></div>;
}

function App() {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({ items: [], item_count: 0, subtotal_cents: 0 });
  const [user, setUser] = useState(null);
  const [orders, setOrders] = useState([]);
  const [page, setPage] = useState('home');
  const [category, setCategory] = useState('All');
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [accountMenu, setAccountMenu] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [adminData, setAdminData] = useState({ products: [], orders: [], customers: [], contacts: [], profile: null, audit: [] });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [apiStatus, setApiStatus] = useState('loading');

  const loadProducts = useCallback(async () => {
    const rows = await api('/api/products');
    setProducts(rows);
    return rows;
  }, []);
  const loadCart = useCallback(async () => {
    if (!user) { setCart({ items: [], item_count: 0, subtotal_cents: 0 }); return; }
    try { setCart(await api('/api/cart')); }
    catch { setCart({ items: [], item_count: 0, subtotal_cents: 0 }); }
  }, [user]);
  const loadOrders = useCallback(async () => {
    if (!user) return;
    try { setOrders(await api('/api/orders')); } catch { setOrders([]); }
  }, [user]);

  useEffect(() => {
    let alive = true;
    Promise.all([api('/api/products'), api('/api/auth/me').catch(() => null)]).then(([rows, profile]) => {
      if (!alive) return;
      setProducts(rows); setUser(profile); setApiStatus('online');
    }).catch(() => alive && setApiStatus('offline'));
    return () => { alive = false; };
  }, []);
  useEffect(() => { loadCart(); loadOrders(); }, [user, loadCart, loadOrders]);
  useEffect(() => {
    if (!notice) return undefined;
    const id = setTimeout(() => setNotice(''), 3200);
    return () => clearTimeout(id);
  }, [notice]);

  const shownProducts = useMemo(() => products.filter((product) => {
    const catOk = category === 'All' || product.category === category;
    const text = `${product.name} ${product.category} ${product.description}`.toLowerCase();
    return catOk && text.includes(search.trim().toLowerCase());
  }), [products, category, search]);

  async function addToCart(product) {
    if (!user) { setSelectedProduct(product); setAuthMode('login'); setAuthOpen(true); return; }
    setBusy(true);
    try { setCart(await api('/api/cart/items', { method: 'POST', body: JSON.stringify({ product_id: product.id, quantity: 1 }) })); setNotice(`${product.name} added to your bag`); }
    catch (err) { setNotice(err.message); }
    finally { setBusy(false); }
  }
  async function changeQuantity(item, quantity) {
    try { setCart(await api(`/api/cart/items/${item.id}`, { method: 'PATCH', body: JSON.stringify({ quantity }) })); }
    catch (err) { setNotice(err.message); }
  }
  async function removeItem(item) {
    try { setCart(await api(`/api/cart/items/${item.id}`, { method: 'DELETE' })); }
    catch (err) { setNotice(err.message); }
  }
  async function authenticate(payload) {
    setBusy(true);
    try {
      const profile = await api(authMode === 'register' ? '/api/auth/register' : '/api/auth/login', { method: 'POST', body: JSON.stringify(payload) });
      setUser(profile); setAuthOpen(false); setNotice(`Welcome${profile.full_name ? `, ${profile.full_name.split(' ')[0]}` : ''}`);
      if (selectedProduct) { const pending = selectedProduct; setSelectedProduct(null); setCart(await api('/api/cart/items', { method: 'POST', body: JSON.stringify({ product_id: pending.id, quantity: 1 }) })); setNotice(`${pending.name} added to your bag`); }
    } finally { setBusy(false); }
  }
  async function signOut() {
    await api('/api/auth/logout', { method: 'POST' }).catch(() => {});
    setUser(null); setOrders([]); setCart({ items: [], item_count: 0, subtotal_cents: 0 }); setPage('home'); setAccountMenu(false); setNotice('You have signed out');
  }
  async function placeOrder(payload) {
    const order = await api('/api/orders', { method: 'POST', body: JSON.stringify(payload) });
    setCheckoutOpen(false); setCartOpen(false); setCart({ items: [], item_count: 0, subtotal_cents: 0 });
    await loadOrders(); setPage('account'); setNotice(`Order ${order.reference} received`);
  }
  async function openAdmin() {
    if (!user || user.role !== 'admin') return;
    setBusy(true);
    try {
      const [productRows, orderRows, customerRows, contacts, profile, audit] = await Promise.all([
        api('/api/admin/products'), api('/api/admin/orders'), api('/api/admin/customers'),
        api('/api/admin/contact-messages'),
        api('/api/admin/security-profile'), api('/api/admin/audit'),
      ]);
      setAdminData({ products: productRows, orders: orderRows, customers: customerRows, contacts, profile, audit });
      setPage('admin'); setAccountMenu(false);
    } catch (err) { setNotice(err.message); }
    finally { setBusy(false); }
  }
  async function refreshAdmin() {
    if (!user || user.role !== 'admin') return;
    const [productsRows, orderRows, customerRows, contacts, profile, audit] = await Promise.all([
      api('/api/admin/products'), api('/api/admin/orders'), api('/api/admin/customers'),
      api('/api/admin/contact-messages'),
      api('/api/admin/security-profile'), api('/api/admin/audit'),
    ]);
    setAdminData({ products: productsRows, orders: orderRows, customers: customerRows, contacts, profile, audit });
  }
  async function saveProduct(payload, id) {
    await api(id ? `/api/admin/products/${id}` : '/api/admin/products', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    await refreshAdmin(); await loadProducts(); setNotice(id ? 'Product updated' : 'Product added to catalogue');
  }
  async function changeOrderStatus(orderId, orderStatus) {
    await api(`/api/admin/orders/${orderId}/status`, { method: 'PATCH', body: JSON.stringify({ status: orderStatus }) });
    await refreshAdmin(); setNotice('Order status updated');
  }
  async function applyProfile(profile) {
    try {
      await api('/api/admin/security-profile', { method: 'POST', body: JSON.stringify({ profile, note: `Researcher selected ${profile}` }) });
      await refreshAdmin(); setNotice(`${profile} profile applied`);
    } catch (err) { setNotice(err.message); }
  }

  const navigate = (next) => { setPage(next); setCategory('All'); setSearch(''); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  const openAccount = () => { if (user) navigate('account'); else { setAuthMode('login'); setAuthOpen(true); } };

  return <div className="store-shell">
    <div className="announcement"><span>Thoughtful goods for your everyday</span><span className="announcement-right">Complimentary delivery on orders over $100 <ArrowRight size={12}/></span></div>
    <header className="store-header"><button className="mobile-menu" aria-label="Open menu" onClick={() => document.body.classList.toggle('nav-open')}><Menu size={20}/></button><button className="wordmark" onClick={() => navigate('home')}><span className="wordmark-icon"><span/></span><span>demo<span>commerce</span><small>OBJECTS FOR LIVING</small></span></button><nav className="store-nav"><button className={page === 'home' && category === 'All' ? 'nav-current' : ''} onClick={() => { navigate('home'); setCategory('All'); }}>Shop</button><button className={page === 'home' && category === 'Home' ? 'nav-current' : ''} onClick={() => { navigate('home'); setCategory('Home'); }}>Home</button><button onClick={() => { navigate('home'); setCategory('Audio'); }}>Audio</button><button onClick={() => navigate('about')}>Our story</button><button onClick={() => navigate('contact')}>Contact</button></nav><div className="header-actions"><button className={`header-icon ${searchOpen ? 'active' : ''}`} onClick={() => setSearchOpen(!searchOpen)} aria-label="Search"><Search size={19}/></button><div className="account-wrap"><button className="header-icon account-trigger" onClick={() => user ? setAccountMenu(!accountMenu) : openAccount()} aria-label="Account"><UserRound size={19}/></button>{accountMenu && <div className="account-popover"><div className="account-popover-head"><strong>{user?.full_name}</strong><span>{user?.email}</span></div><button onClick={() => { navigate('account'); setAccountMenu(false); }}><CircleUserRound size={15}/>My account</button>{user?.role === 'admin' && <button onClick={openAdmin}><Settings2 size={15}/>Admin workspace</button>}<button onClick={signOut}><LogOut size={15}/>Sign out</button></div>}</div><button className="bag-button" onClick={() => setCartOpen(true)} aria-label={`Shopping bag, ${itemCount(cart)} items`}><ShoppingBag size={18}/><span>Bag</span><i>{itemCount(cart)}</i></button></div></header>
    {searchOpen && <div className="search-bar"><Search size={17}/><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === 'Escape' && setSearchOpen(false)} placeholder="Search considered goods…"/><button onClick={() => setSearchOpen(false)} aria-label="Close search"><X size={17}/></button></div>}
    <div className="mobile-nav"><button onClick={() => { navigate('home'); document.body.classList.remove('nav-open'); }}>Shop</button><button onClick={() => { navigate('home'); setCategory('Home'); document.body.classList.remove('nav-open'); }}>Home</button><button onClick={() => { navigate('home'); setCategory('Audio'); document.body.classList.remove('nav-open'); }}>Audio</button><button onClick={() => { navigate('about'); document.body.classList.remove('nav-open'); }}>Our story</button><button onClick={() => { navigate('contact'); document.body.classList.remove('nav-open'); }}>Contact</button></div>
    {apiStatus === 'offline' && <div className="offline-banner"><span/>The DemoCommerce service is unavailable. Start the local API to browse live products.</div>}

    <main>
      {page === 'home' && <StoreHome products={shownProducts} category={category} setCategory={setCategory} onProduct={setSelectedProduct} onAdd={addToCart} onAbout={() => navigate('about')} busy={busy} search={search} clearSearch={() => setSearch('')} />}
      {page === 'about' && <AboutPage onShop={() => navigate('home')}/>}
      {page === 'contact' && <ContactPage onNotice={setNotice}/>}
      {page === 'account' && user && <AccountPage user={user} orders={orders} onProfileUpdate={async (payload) => { const updated = await api('/api/auth/me', { method: 'PATCH', body: JSON.stringify(payload) }); setUser(updated); setNotice('Your details have been saved'); }} />}
      {page === 'admin' && user?.role === 'admin' && <AdminPage data={adminData} onSaveProduct={saveProduct} onOrderStatus={changeOrderStatus} onProfile={applyProfile} onRefresh={refreshAdmin}/>}
      {page === 'account' && !user && <div className="account-gate"><CircleUserRound size={34}/><h2>Your account, all in one place.</h2><p>Sign in to view your orders and update your details.</p><button className="button button-dark" onClick={openAccount}>Sign in <ArrowRight size={15}/></button></div>}
    </main>
    <StoreFooter onNavigate={navigate}/>
    {cartOpen && <CartDrawer cart={cart} user={user} onClose={() => setCartOpen(false)} onQuantity={changeQuantity} onRemove={removeItem} onCheckout={() => { if (!user) { setCartOpen(false); setAuthMode('login'); setAuthOpen(true); } else setCheckoutOpen(true); }} onShop={() => { setCartOpen(false); navigate('home'); }} />}
    {authOpen && <AuthModal mode={authMode} setMode={setAuthMode} busy={busy} onClose={() => { setAuthOpen(false); setSelectedProduct(null); }} onSubmit={authenticate}/>}
    {selectedProduct && !authOpen && <ProductModal product={selectedProduct} onClose={() => setSelectedProduct(null)} onAdd={() => { const item = selectedProduct; setSelectedProduct(null); addToCart(item); }} />}
    {checkoutOpen && <CheckoutModal cart={cart} user={user} onClose={() => setCheckoutOpen(false)} onPlace={placeOrder}/>}
    {notice && <div className="store-toast"><CheckCircle2 size={16}/>{notice}<button onClick={() => setNotice('')} aria-label="Dismiss"><X size={14}/></button></div>}
    <div className="connection-indicator" title={apiStatus === 'online' ? 'Connected to local API' : 'Connecting to local API'}><i className={apiStatus}/><span>{apiStatus === 'online' ? 'Local store' : apiStatus === 'offline' ? 'Service offline' : 'Connecting'}</span></div>
  </div>;
}

function StoreHome({ products, category, setCategory, onProduct, onAdd, onAbout, busy, search, clearSearch }) {
  return <>
    <section className="hero"><div className="hero-copy"><div className="hero-kicker"><span/>THE EVERYDAY EDITION · NO. 04</div><h1>Good things,<br/><em>well made.</em></h1><p>Useful, lasting pieces chosen to make the everyday feel a little more considered.</p><button className="button button-dark" onClick={() => document.getElementById('catalogue')?.scrollIntoView({ behavior: 'smooth' })}>Explore the collection <ArrowRight size={15}/></button><div className="hero-trust"><span><BadgeCheck size={14}/>Made to last</span><i/><span>Designed with intention</span></div></div><div className="hero-visual"><div className="hero-circle circle-back"/><div className="hero-circle circle-front"/><div className="hero-object hero-vase"><div/><span/></div><div className="hero-object hero-lamp"><i/><b/><span/></div><div className="hero-object hero-book"><i/><i/><i/></div><div className="hero-visual-caption"><span>FORM / FUNCTION</span><span>01 — 08</span></div><div className="hero-note"><span>Thoughtful by design</span><ArrowDown size={14}/></div></div><div className="hero-index">01<span>/</span>03</div></section>
    <section className="value-bar"><div><PackageCheck size={17}/><span>Objects with purpose</span></div><i/><div><Leaf size={17}/><span>Materials that matter</span></div><i/><div><Truck size={17}/><span>Complimentary delivery over $100</span></div><i/><div><ShieldCheck size={17}/><span>Easy, considered returns</span></div></section>
    <section className="catalogue section-wrap" id="catalogue"><div className="section-intro"><div><span className="section-eyebrow">THE COLLECTION <i/></span><h2>Objects for a life <em>well lived.</em></h2></div><p>Fewer things, better chosen. Explore our edit of home, audio and everyday essentials.</p></div><div className="catalogue-toolbar"><div className="category-tabs">{CATEGORIES.map((item) => <button key={item} onClick={() => setCategory(item)} className={category === item ? 'selected' : ''}>{item}</button>)}</div><span className="catalogue-count">{products.length} considered pieces <SlidersHorizontal size={14}/></span></div>{search && <div className="search-result-note">Showing matches for <strong>“{search}”</strong><button onClick={clearSearch}>Clear search <X size={13}/></button></div>}{products.length ? <div className="product-grid">{products.map((product, index) => <ProductCard key={product.id} product={product} index={index} onProduct={() => onProduct(product)} onAdd={() => onAdd(product)} busy={busy}/>)}</div> : <div className="no-products"><Search size={24}/><strong>No pieces found</strong><span>Try another category or search phrase.</span></div>}<div className="collection-note"><span>DC / 2026</span><span>Every object has a story. <button>Read ours <ArrowRight size={13}/></button></span><span>SCROLL TO EXPLORE <ArrowDown size={12}/></span></div></section>
    <section className="editorial"><div className="editorial-art"><div className="editorial-sun"/><div className="editorial-chair"><i/><b/><span/></div><div className="editorial-plant"><i/><i/><i/><b/></div><span className="editorial-stamp">SLOW<br/>LIVING<br/>STUDIO</span></div><div className="editorial-copy"><span className="section-eyebrow">A LITTLE MORE INTENTION <i/></span><h2>Make room for<br/><em>what matters.</em></h2><p>We believe good design should feel effortless. Our collection brings together functional pieces, natural materials and forms that find their place in your everyday.</p><button className="text-link" onClick={onAbout}>A note from our founders <ArrowRight size={15}/></button><span className="editorial-number">02 — 04</span></div></section>
    <section className="newsletter"><span className="section-eyebrow">THE SUNDAY LETTER <i/></span><h2>A slower kind of <em>inbox.</em></h2><p>New arrivals, little rituals and notes from the studio. Once in a while, never too often.</p><NewsletterForm/></section>
  </>;
}

function ProductCard({ product, index, onProduct, onAdd }) {
  return <article className={`product-card card-index-${index % 4}`}><div className="product-image-button"><button className="product-art-trigger" onClick={onProduct} aria-label={`View ${product.name}`}><ProductArt category={product.category}/>{product.compare_at_cents && <span className="product-tag">A SMALL FAVORITE</span>}</button><button className="quick-add" onClick={onAdd} aria-label={`Add ${product.name} to bag`}><Plus size={17}/></button></div><div className="product-meta"><span>{product.category.toUpperCase()} <i/> {product.stock > 0 ? 'IN STOCK' : 'SOLD OUT'}</span><button className="favorite" aria-label="Save item"><Heart size={16}/></button></div><button className="product-title" onClick={onProduct}>{product.name}</button><div className="product-price">{money(product.price_cents)}{product.compare_at_cents && <del>{money(product.compare_at_cents)}</del>}</div></article>;
}

function StoreFooter({ onNavigate }) {
  return <footer className="store-footer"><div className="footer-main"><div className="footer-brand"><button className="wordmark" onClick={() => onNavigate('home')}><span className="wordmark-icon"><span/></span><span>demo<span>commerce</span><small>OBJECTS FOR LIVING</small></span></button><p>Considered objects for everyday living.<br/>Designed with intention, made to last.</p><div className="social-dots"><span>ig</span><span>in</span><span>p</span></div></div><div className="footer-col"><strong>Explore</strong><button onClick={() => onNavigate('home')}>Shop all</button><button onClick={() => onNavigate('home')}>New arrivals</button><button onClick={() => onNavigate('about')}>Our story</button></div><div className="footer-col"><strong>Help</strong><button>Delivery & returns</button><button>Care guide</button><button onClick={() => onNavigate('contact')}>Contact us</button></div><div className="footer-col"><strong>Account</strong><button onClick={() => onNavigate('account')}>My account</button><button>Order tracking</button><button>Privacy</button></div><div className="footer-mark">D<span>C</span></div></div><div className="footer-bottom"><span>© 2026 DemoCommerce. Made for the everyday.</span><span>FICTIONAL STOREFRONT · NO REAL PAYMENTS COLLECTED</span><span>Designed to feel considered <Sparkles size={12}/></span></div></footer>;
}

function AboutPage({ onShop }) {
  return <section className="about-page"><div className="about-hero"><span className="section-eyebrow">A NOTE FROM OUR FOUNDERS <i/></span><h1>Buy less.<br/><em>Choose well.</em></h1><p>DemoCommerce began with a simple thought: the things we keep around us should earn their place.</p></div><div className="about-body"><div className="about-art"><div/><span>FORM FOLLOWS FEELING</span></div><div><span className="section-eyebrow">OUR POINT OF VIEW <i/></span><h2>Useful things can<br/>still be <em>beautiful.</em></h2><p>We make a small, changing collection of objects for home and everyday life. Each piece is selected for its material, its usefulness and the quiet way it makes a space feel more like yours.</p><p>This is a fictional retail experience built for software testing. All products, customers, orders and transactions are illustrative only. No payment information is collected and no goods are sold.</p><button className="button button-dark" onClick={onShop}>Explore the collection <ArrowRight size={15}/></button></div></div></section>;
}

function ContactPage({ onNotice }) {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [sending, setSending] = useState(false); const [sent, setSent] = useState(''); const [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault(); setSending(true); setError('');
    try { const result = await api('/api/contact', { method: 'POST', body: JSON.stringify(form) }); setSent(result.reference); setForm({ name: '', email: '', subject: '', message: '' }); onNotice(`Your message was received · ${result.reference}`); }
    catch (err) { setError(err.message); }
    finally { setSending(false); }
  }
  return <section className="contact-page"><div className="contact-hero"><span className="section-eyebrow">WE’RE HERE TO HELP <i/></span><h1>A note is always<br/><em>welcome.</em></h1><p>Questions about a piece, a delivery or simply want to say hello? Leave a note for our small team.</p></div><div className="contact-content"><div className="contact-aside"><span className="section-eyebrow">THE STUDIO <i/></span><h2>Good conversations<br/>start simply.</h2><p>This is a fictional store for software testing. Contact messages are stored in this local application and visible only to its researcher administrator.</p><div className="contact-detail"><span>RESPONSE TIME</span><strong>Usually within two working days</strong></div><div className="contact-detail"><span>YOUR REFERENCE</span><strong>Every note receives a traceable ID</strong></div><span className="contact-mark">D<span>C</span></span></div><form className="contact-form" onSubmit={submit}><div className="contact-form-heading"><strong>Send us a note</strong><span>All fields are required.</span></div><div className="contact-fields"><label>Your name<input required minLength="2" maxLength="120" value={form.name} onChange={(e) => setForm({...form,name:e.target.value})} placeholder="How should we address you?"/></label><label>Email address<input type="email" required value={form.email} onChange={(e) => setForm({...form,email:e.target.value})} placeholder="you@example.com"/></label></div><label>Subject<input required minLength="3" maxLength="140" value={form.subject} onChange={(e) => setForm({...form,subject:e.target.value})} placeholder="What can we help with?"/></label><label>Your message<textarea required minLength="10" maxLength="3000" value={form.message} onChange={(e) => setForm({...form,message:e.target.value})} placeholder="A little more detail helps us get back to you…"/></label>{error && <div className="auth-error">{error}</div>}{sent && <div className="contact-success"><CheckCircle2 size={15}/>Message received · {sent}</div>}<button className="button button-dark" disabled={sending}>{sending ? 'Sending…' : 'Send your note'}<ArrowRight size={15}/></button><small>Fictional application · Please don’t submit personal or sensitive information.</small></form></div></section>;
}

function AccountPage({ user, orders, onProfileUpdate }) {
  const [editing, setEditing] = useState(false);
  const [openOrder, setOpenOrder] = useState(null);
  const [fullName, setFullName] = useState(user.full_name);
  const [phone, setPhone] = useState(user.phone || '');
  const [saving, setSaving] = useState(false);
  async function save(event) { event.preventDefault(); setSaving(true); try { await onProfileUpdate({ full_name: fullName, phone }); setEditing(false); } finally { setSaving(false); } }
  return <section className="account-page"><div className="account-intro"><span className="section-eyebrow">YOUR DEMOCOMMERCE <i/></span><h1>Hello, <em>{user.full_name.split(' ')[0]}.</em></h1><p>A little space for your details, delivery updates and order history.</p></div><div className="account-layout"><aside className="account-sidebar"><span>YOUR ACCOUNT</span><button className="active"><CircleUserRound size={15}/>Overview</button><button onClick={() => document.querySelector('.orders-card')?.scrollIntoView({behavior:'smooth'})}><Package size={15}/>Order history <i>{orders.length}</i></button><button onClick={() => setEditing(true)}><UserRound size={15}/>Profile details</button></aside><div className="account-content"><section className="account-card profile-card"><div className="account-card-head"><div><span className="section-eyebrow">YOUR DETAILS <i/></span><h2>Personal information</h2></div><button className="text-link" onClick={() => setEditing(!editing)}>{editing ? 'Cancel' : 'Edit details'} <ArrowRight size={14}/></button></div>{editing ? <form className="profile-form" onSubmit={save}><label>Full name<input required minLength="2" value={fullName} onChange={(e) => setFullName(e.target.value)}/></label><label>Email address<input value={user.email} disabled/></label><label>Phone number<input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Optional"/></label><button className="button button-dark" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button></form> : <div className="profile-fields"><div><span>Full name</span><strong>{user.full_name}</strong></div><div><span>Email address</span><strong>{user.email}</strong></div><div><span>Phone number</span><strong>{user.phone || 'Not added'}</strong></div></div>}</section><section className="account-card orders-card"><div className="account-card-head"><div><span className="section-eyebrow">THE GOOD THINGS <i/></span><h2>Your orders</h2></div><span className="order-count">{orders.length} total</span></div>{orders.length ? <div className="orders-list">{orders.map((order) => <div key={order.id}><button className="order-row" onClick={() => setOpenOrder(openOrder === order.id ? null : order.id)} aria-expanded={openOrder === order.id}><span className="order-box"><PackageCheck size={17}/></span><span><strong>{order.reference}</strong><span>{new Date(order.created_at).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })} · {order.items.length} item{order.items.length === 1 ? '' : 's'}</span></span><span className={`order-status status-${order.status}`}>{order.status}</span><strong>{money(order.total_cents)}</strong><ChevronRight size={15}/></button>{openOrder === order.id && <div className="order-details">{order.items.map((item) => <div className="order-detail-line" key={item.id}><span>{item.quantity} × {item.product_name}</span><strong>{money(item.unit_price_cents * item.quantity)}</strong></div>)}<div className="order-summary-total"><span>Simulated order total</span><strong>{money(order.total_cents)}</strong></div><span className="order-detail-line">Delivery status: {order.status}</span></div>}</div>)}</div> : <div className="orders-empty"><Package size={22}/><strong>Your story starts here.</strong><span>When you find something you love, it will show up here.</span></div>}</section></div></div></section>;
}

function CartDrawer({ cart, user, onClose, onQuantity, onRemove, onCheckout, onShop }) {
  return <div className="drawer-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><aside className="cart-drawer"><div className="drawer-head"><div><span className="section-eyebrow">YOUR SELECTION <i/></span><h2>Bag <span>({itemCount(cart)})</span></h2></div><button className="close-button" onClick={onClose} aria-label="Close bag"><X size={19}/></button></div>{cart.items.length ? <><div className="cart-items">{cart.items.map((item) => <div className="cart-item" key={item.id}><div className="cart-thumb"><ProductArt category={item.product.category}/></div><div className="cart-item-info"><span>{item.product.category.toUpperCase()}</span><strong>{item.product.name}</strong><b>{money(item.product.price_cents)}</b><div className="quantity-control"><button onClick={() => item.quantity > 1 ? onQuantity(item, item.quantity - 1) : onRemove(item)} aria-label="Decrease quantity"><Minus size={12}/></button><span>{item.quantity}</span><button onClick={() => onQuantity(item, item.quantity + 1)} aria-label="Increase quantity"><Plus size={12}/></button><button className="remove-item" onClick={() => onRemove(item)}>Remove</button></div></div></div>)}</div><div className="drawer-bottom"><div className="shipping-progress"><span className="shipping-icon"><Truck size={15}/></span><span>{cart.subtotal_cents >= 10000 ? 'Your delivery is on us.' : `You’re ${money(10000 - cart.subtotal_cents)} away from complimentary delivery.`}</span></div><div className="subtotal-row"><span>Subtotal</span><strong>{money(cart.subtotal_cents)}</strong></div><p>Delivery and taxes are calculated at checkout.</p><button className="button button-dark checkout-button" onClick={onCheckout}>Continue to checkout <ArrowRight size={15}/></button><span className="payment-note"><CreditCard size={13}/> Simulated checkout — no payment collected</span></div></> : <div className="cart-empty"><div className="empty-bag"><ShoppingBag size={25}/></div><h3>A little room for something good.</h3><p>Your bag is currently empty. Take a look around and see what speaks to you.</p><button className="button button-dark" onClick={onShop}>Explore the collection <ArrowRight size={14}/></button><span><ShieldCheck size={13}/> All transactions are simulated</span></div>}</aside></div>;
}

function AuthModal({ mode, setMode, busy, onClose, onSubmit }) {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [fullName, setFullName] = useState(''); const [error, setError] = useState('');
  async function submit(event) { event.preventDefault(); setError(''); try { await onSubmit(mode === 'register' ? { email, password, full_name: fullName } : { email, password }); } catch (err) { setError(err.message); } }
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><section className="auth-modal" role="dialog" aria-modal="true"><button className="close-button auth-close" onClick={onClose} aria-label="Close"><X size={18}/></button><div className="auth-emblem"><span className="wordmark-icon"><span/></span></div><span className="section-eyebrow">YOUR DEMOCOMMERCE <i/></span><h2>{mode === 'login' ? 'Welcome back.' : 'A good place to start.'}</h2><p>{mode === 'login' ? 'Sign in to pick up where you left off.' : 'Create an account for your orders and details.'}</p><form onSubmit={submit}>{mode === 'register' && <label>Full name<input autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength="2" placeholder="Your name"/></label>}<label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@example.com"/></label><label>Password<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === 'login' ? 1 : 10} placeholder={mode === 'login' ? 'Your password' : 'At least 10 characters'}/></label>{error && <div className="auth-error">{error}</div>}<button className="button button-dark auth-submit" disabled={busy}>{busy ? 'One moment…' : mode === 'login' ? 'Sign in' : 'Create your account'} <ArrowRight size={15}/></button></form><div className="auth-switch">{mode === 'login' ? 'New to DemoCommerce?' : 'Already have an account?'} <button onClick={() => { setError(''); setMode(mode === 'login' ? 'register' : 'login'); }}>{mode === 'login' ? 'Create account' : 'Sign in'}</button></div><div className="auth-demo-note"><ShieldCheck size={13}/> Demo storefront · fictional customer data only</div></section></div>;
}

function CheckoutModal({ cart, user, onClose, onPlace }) {
  const [shippingName, setShippingName] = useState(user?.full_name || ''); const [address, setAddress] = useState(''); const [error, setError] = useState(''); const [saving, setSaving] = useState(false);
  async function submit(event) { event.preventDefault(); setSaving(true); setError(''); try { await onPlace({ shipping_name: shippingName, shipping_address: address }); } catch (err) { setError(err.message); } finally { setSaving(false); } }
  return <div className="modal-backdrop"><section className="checkout-modal" role="dialog" aria-modal="true"><div className="checkout-top"><div><span className="section-eyebrow">A SMALL CHECKOUT <i/></span><h2>Almost yours.</h2></div><button className="close-button" onClick={onClose}><X size={18}/></button></div><div className="checkout-step"><span className="step-num">01</span><div><strong>Delivery details</strong><span>Where should we send your order?</span></div></div><form onSubmit={submit}><label>Full name<input required minLength="2" value={shippingName} onChange={(e) => setShippingName(e.target.value)}/></label><label>Delivery address<textarea required minLength="5" maxLength="300" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Street, city, postal code"/></label><div className="checkout-summary"><span>{itemCount(cart)} item{itemCount(cart) === 1 ? '' : 's'}</span><strong>{money(cart.subtotal_cents)}</strong></div><div className="simulated-payment"><CreditCard size={15}/><span>No payment will be collected. This creates a simulated order for the test environment.</span></div>{error && <div className="auth-error">{error}</div>}<button className="button button-dark auth-submit" disabled={saving}>{saving ? 'Creating order…' : 'Place simulated order'} <ArrowRight size={15}/></button></form></section></div>;
}

function ProductModal({ product, onClose, onAdd }) {
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><section className="product-modal" role="dialog" aria-modal="true"><button className="close-button product-close" onClick={onClose} aria-label="Close"><X size={18}/></button><ProductArt category={product.category} large/><div className="product-modal-copy"><span className="section-eyebrow">{product.category.toUpperCase()} <i/></span><h2>{product.name}</h2><strong className="detail-price">{money(product.price_cents)} {product.compare_at_cents && <del>{money(product.compare_at_cents)}</del>}</strong><p>{product.description}</p><div className="product-detail-line"><span><Check size={13}/> Thoughtfully selected</span><span><Check size={13}/> {product.stock ? `${product.stock} available` : 'Sold out'}</span></div><button className="button button-dark auth-submit" onClick={onAdd} disabled={!product.stock}>Add to bag — {money(product.price_cents)} <ArrowRight size={15}/></button><span className="detail-returns"><Truck size={14}/>Complimentary delivery over $100 · Easy returns</span></div></section></div>;
}

function NewsletterForm() {
  const [email, setEmail] = useState(''); const [done, setDone] = useState(false);
  return <form className="newsletter-form" onSubmit={(e) => { e.preventDefault(); setDone(true); }}><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="Your email address" aria-label="Your email address"/><button type="submit" aria-label="Subscribe">{done ? <Check size={17}/> : <ArrowRight size={17}/>}</button>{done && <span>This newsletter sign-up is simulated and was not saved.</span>}</form>;
}

function AdminPage({ data, onSaveProduct, onOrderStatus, onProfile, onRefresh }) {
  const [tab, setTab] = useState('overview'); const [productModal, setProductModal] = useState(null); const [confirm, setConfirm] = useState(false);
  const profile = data.profile?.profile || 'BASELINE';
  return <section className="admin-page"><div className="admin-heading"><div><span className="section-eyebrow">DEMOCOMMERCE / RESEARCHER <i/></span><h1>Store management.</h1><p>Business operations and controlled application configuration.</p></div><div className="admin-chip"><ShieldCheck size={15}/>Administrator</div></div><div className="admin-tabs">{[['overview','Overview'],['products','Products'],['orders','Orders'],['customers','Customers'],['contact','Contact inbox'],['configuration','Configuration']].map(([id,label]) => <button className={tab === id ? 'active' : ''} key={id} onClick={() => { setTab(id); if (id === 'configuration') onRefresh(); }}>{label}{id === 'orders' && data.orders.length > 0 && <i>{data.orders.length}</i>}</button>)}</div>
    {tab === 'overview' && <><div className="admin-metrics"><div><span>Active products</span><strong>{data.products.filter((p) => p.active).length}</strong><small>in the catalogue</small></div><div><span>Orders received</span><strong>{data.orders.length}</strong><small>simulated orders</small></div><div><span>Customers</span><strong>{data.customers.length}</strong><small>registered accounts</small></div><div><span>HTTP profile</span><strong className="profile-value">{profile.replace('_',' ')}</strong><small>security configuration</small></div></div><div className="admin-dashboard-grid"><section className="admin-panel"><div className="admin-panel-head"><div><span className="section-eyebrow">RECENT ACTIVITY <i/></span><h2>Latest orders</h2></div><button className="text-link" onClick={() => setTab('orders')}>View all <ArrowRight size={13}/></button></div>{data.orders.length ? <AdminOrders orders={data.orders.slice(0,5)} onStatus={onOrderStatus}/> : <div className="admin-empty"><Package size={20}/><span>No orders yet. Customer test orders will appear here.</span></div>}</section><section className="admin-panel config-preview"><div className="admin-panel-head"><div><span className="section-eyebrow">CONTROLLED CONFIGURATION <i/></span><h2>Active profile</h2></div><Settings2 size={17}/></div><div className="profile-display"><span className={`profile-badge ${profile.toLowerCase()}`}>{profile}</span><p>{profile === 'TEST_CHANGE' ? 'Selected security headers are relaxed and CORS is open for local controlled assessment.' : 'Secure response headers and an origin allowlist are active.'}</p></div><button className="text-link" onClick={() => { setTab('configuration'); onRefresh(); }}>Manage profiles <ArrowRight size={13}/></button></section></div></>}
    {tab === 'products' && <section className="admin-panel admin-table-panel"><div className="admin-panel-head"><div><span className="section-eyebrow">CATALOGUE <i/></span><h2>Product management</h2></div><button className="button button-dark admin-add" onClick={() => setProductModal({})}><Plus size={14}/>Add product</button></div><div className="admin-table-scroll"><table className="admin-table"><thead><tr><th>Product</th><th>Category</th><th>Price</th><th>Stock</th><th>Visibility</th><th/></tr></thead><tbody>{data.products.map((product) => <tr key={product.id}><td><strong>{product.name}</strong><span>{product.slug}</span></td><td>{product.category}</td><td>{money(product.price_cents)}</td><td>{product.stock}</td><td><span className={product.active ? 'visibility active' : 'visibility'}>{product.active ? 'Visible' : 'Archived'}</span></td><td><button className="text-link" onClick={() => setProductModal(product)}>Edit <ArrowRight size={12}/></button></td></tr>)}</tbody></table></div></section>}
    {tab === 'orders' && <section className="admin-panel admin-table-panel"><div className="admin-panel-head"><div><span className="section-eyebrow">CUSTOMER ACTIVITY <i/></span><h2>Order management</h2></div><span className="admin-count">{data.orders.length} orders</span></div>{data.orders.length ? <AdminOrders orders={data.orders} onStatus={onOrderStatus}/> : <div className="admin-empty"><Package size={20}/><span>Orders created through simulated checkout will appear here.</span></div>}</section>}
    {tab === 'customers' && <section className="admin-panel admin-table-panel"><div className="admin-panel-head"><div><span className="section-eyebrow">CUSTOMER DIRECTORY <i/></span><h2>Customers</h2></div><span className="admin-count">{data.customers.length} accounts</span></div>{data.customers.length ? <div className="admin-table-scroll"><table className="admin-table"><thead><tr><th>Customer</th><th>Email</th><th>Phone</th><th>Orders</th><th>Joined</th></tr></thead><tbody>{data.customers.map((customer) => <tr key={customer.id}><td><strong>{customer.full_name}</strong></td><td>{customer.email}</td><td>{customer.phone || '—'}</td><td>{customer.order_count}</td><td>{new Date(customer.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div> : <div className="admin-empty"><UserRound size={20}/><span>Customer accounts appear here when they register.</span></div>}</section>}
    {tab === 'contact' && <section className="admin-panel admin-table-panel"><div className="admin-panel-head"><div><span className="section-eyebrow">CUSTOMER MESSAGES <i/></span><h2>Contact inbox</h2></div><span className="admin-count">{data.contacts?.length || 0} messages</span></div>{data.contacts?.length ? <div className="message-list">{data.contacts.map((message) => <article key={message.id}><div><strong>{message.subject}</strong><span>{message.name} · {message.email} · {new Date(message.created_at).toLocaleString()}</span></div><BadgeStatus status={message.status}/><p>{message.message}</p></article>)}</div> : <div className="admin-empty"><CircleUserRound size={20}/><span>Contact form messages will appear here. No real personal details should be submitted to this test application.</span></div>}</section>}
    {tab === 'configuration' && <div className="config-page"><section className="admin-panel profile-control"><div className="admin-panel-head"><div><span className="section-eyebrow">HTTP SECURITY SETTINGS <i/></span><h2>Configuration profiles</h2></div><span className={`profile-badge ${profile.toLowerCase()}`}>{profile}</span></div><p>Change the observable security configuration for a local controlled assessment. Profiles are reversible and recorded in the audit history.</p><div className="profile-options">{[['BASELINE','Secure baseline','Strict response headers, origin-restricted credentialed CORS and secure session attributes.'],['TEST_CHANGE','Controlled test change','Removes CSP and frame protection, reflects any origin with credentials, and relaxes cookie attributes. Local test mode only.'],['RESTORED','Restored baseline','Restores the original secure response headers, CORS allowlist and session cookie settings.']].map(([value,label,detail]) => <button key={value} className={`profile-option ${profile === value ? 'selected' : ''}`} onClick={() => value === 'TEST_CHANGE' ? setConfirm(true) : onProfile(value)} disabled={value === 'TEST_CHANGE' && !data.profile?.test_profiles_enabled}><span className="profile-radio">{profile === value && <i/>}</span><span><strong>{label}</strong><small>{detail}</small></span>{profile === value && <CheckCircle2 size={16}/>}</button>)}</div>{!data.profile?.test_profiles_enabled && <div className="config-warning"><ShieldCheck size={15}/> TEST_CHANGE is disabled by server configuration. Enable <code>DEMO_TEST_PROFILES_ENABLED=1</code> for an isolated local instance.</div>}<div className="config-effective"><h3>Effective HTTP settings</h3><div><span>Response headers</span><strong>{Object.keys(data.profile?.effective?.headers || {}).length} active</strong></div><div><span>CORS policy</span><strong>{data.profile?.effective?.cors === '*' ? 'Wildcard' : 'Origin allowlist'}</strong></div><div><span>Session cookie</span><strong>{data.profile?.effective?.cookie?.httponly ? 'HttpOnly' : 'HttpOnly disabled'} · SameSite {data.profile?.effective?.cookie?.samesite}</strong></div></div></section><section className="admin-panel audit-panel"><div className="admin-panel-head"><div><span className="section-eyebrow">CHANGE RECORD <i/></span><h2>Configuration history</h2></div><Clock3 size={16}/></div>{data.profile?.history?.length ? <div className="audit-list">{data.profile.history.map((entry, i) => <div key={`${entry.changed_at}-${i}`}><span className="audit-dot"/><div><strong>{entry.profile}</strong><span>{entry.note}</span></div><time>{new Date(entry.changed_at).toLocaleString()}</time></div>)}</div> : <div className="admin-empty"><Clock3 size={19}/><span>Profile changes and the administrator who made them are logged here.</span></div>}</section></div>}
    {productModal && <ProductAdminModal product={productModal.id ? productModal : null} onClose={() => setProductModal(null)} onSave={async (payload) => { await onSaveProduct(payload, productModal.id); setProductModal(null); }}/>}
    {confirm && <div className="modal-backdrop"><section className="confirm-modal"><span className="confirm-icon"><ShieldCheck size={20}/></span><h2>Apply controlled change?</h2><p>This will change the response headers, cookie attributes and CORS behavior for this local instance. Keep the environment isolated and restore BASELINE after the assessment.</p><div><button className="button button-light" onClick={() => setConfirm(false)}>Cancel</button><button className="button button-dark" onClick={() => { setConfirm(false); onProfile('TEST_CHANGE'); }}>Apply test profile</button></div></section></div>}
  </section>;
}

function AdminOrders({ orders, onStatus }) {
  const statuses = ['received','processing','shipped','delivered','cancelled'];
  return <div className="admin-table-scroll"><table className="admin-table"><thead><tr><th>Order</th><th>Customer</th><th>Date</th><th>Total</th><th>Status</th></tr></thead><tbody>{orders.map((order) => <tr key={order.id}><td><strong>{order.reference}</strong></td><td><strong>{order.customer_name || order.shipping_name}</strong><span>{order.customer_email || order.shipping_address}</span></td><td>{new Date(order.created_at).toLocaleDateString()}</td><td>{money(order.total_cents)}</td><td><select className="order-status-select" value={order.status} onChange={(e) => onStatus(order.id, e.target.value)}>{statuses.map((status) => <option key={status}>{status}</option>)}</select></td></tr>)}</tbody></table></div>;
}

function ProductAdminModal({ product, onClose, onSave }) {
  const [form, setForm] = useState(product ? { ...product } : { slug: '', name: '', category: 'Home', description: '', price_cents: 1000, compare_at_cents: '', stock: 0, featured: false, active: true });
  const [saving, setSaving] = useState(false); const [error, setError] = useState('');
  function field(name, value) { setForm((prev) => ({ ...prev, [name]: value })); }
  async function submit(event) { event.preventDefault(); setSaving(true); setError(''); try { await onSave({ ...form, price_cents: Number(form.price_cents), compare_at_cents: form.compare_at_cents ? Number(form.compare_at_cents) : null, stock: Number(form.stock) }); } catch (err) { setError(err.message); } finally { setSaving(false); } }
  return <div className="modal-backdrop"><section className="product-admin-modal"><div className="checkout-top"><div><span className="section-eyebrow">CATALOGUE MANAGEMENT <i/></span><h2>{product ? 'Edit product' : 'Add a product'}</h2></div><button className="close-button" onClick={onClose}><X size={18}/></button></div><form onSubmit={submit}><label>Product name<input value={form.name} onChange={(e) => field('name', e.target.value)} required minLength="2"/></label><label>Product slug<input value={form.slug} onChange={(e) => field('slug', e.target.value)} required pattern="[a-z0-9]+(-[a-z0-9]+)*"/><small>Lowercase words separated with hyphens.</small></label><div className="admin-form-row"><label>Category<select value={form.category} onChange={(e) => field('category', e.target.value)}>{CATEGORIES.filter((x) => x !== 'All').map((x) => <option key={x}>{x}</option>)}</select></label><label>Stock<input type="number" min="0" value={form.stock} onChange={(e) => field('stock', e.target.value)} required/></label></div><label>Description<textarea value={form.description} onChange={(e) => field('description', e.target.value)} required minLength="10"/></label><div className="admin-form-row"><label>Price in cents<input type="number" min="1" value={form.price_cents} onChange={(e) => field('price_cents', e.target.value)} required/><small>e.g. 2499 = $24.99</small></label><label>Compare at (cents)<input type="number" min="1" value={form.compare_at_cents || ''} onChange={(e) => field('compare_at_cents', e.target.value)}/></label></div><label className="admin-check"><input type="checkbox" checked={form.featured} onChange={(e) => field('featured', e.target.checked)}/>Feature on the home page</label>{error && <div className="auth-error">{error}</div>}<div className="admin-modal-actions"><button type="button" className="button button-light" onClick={onClose}>Cancel</button><button className="button button-dark" disabled={saving}>{saving ? 'Saving…' : 'Save product'}</button></div></form></section></div>;
}

export default App;
