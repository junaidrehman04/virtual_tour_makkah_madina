const express = require('express');
const multer  = require('multer');
const path    = require('path');
const fs      = require('fs');
const cors    = require('cors');

const app  = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ─── Multer Storage ────────────────────────────────────────────────────────
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const loc  = (req.body.location || 'makkah').replace(/[^a-z]/g, '');
    const dest = path.join(__dirname, 'public', 'images', loc);
    fs.mkdirSync(dest, { recursive: true });
    cb(null, dest);
  },
  filename: (req, file, cb) => {
    const ext  = path.extname(file.originalname).toLowerCase();
    const name = (req.body.scene_id || Date.now()).toString().replace(/[^a-z0-9_]/g, '');
    cb(null, `${name}_pano${ext}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 80 * 1024 * 1024 },   // 80 MB max
  fileFilter: (req, file, cb) => {
    const ok = /jpeg|jpg|png|webp/.test(file.mimetype);
    cb(ok ? null : new Error('Only image files allowed'), ok);
  }
});

// ─── API Routes ────────────────────────────────────────────────────────────

// Get full tour configuration
app.get('/api/tour', (req, res) => {
  const cfgPath = path.join(__dirname, 'data', 'tour-config.json');
  if (!fs.existsSync(cfgPath)) return res.status(404).json({ error: 'Config not found' });
  res.json(JSON.parse(fs.readFileSync(cfgPath, 'utf8')));
});

// Upload new panorama image
app.post('/api/upload', upload.single('panorama'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded' });

  const loc     = (req.body.location || 'makkah').replace(/[^a-z]/g, '');
  const sceneId = (req.body.scene_id || '').replace(/[^a-z0-9_]/g, '');
  const imgPath = `/images/${loc}/${req.file.filename}`;

  // Update tour config if scene_id provided
  if (sceneId) {
    const cfgPath = path.join(__dirname, 'data', 'tour-config.json');
    try {
      const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
      const tour = cfg[loc];
      if (tour) {
        const step = tour.find(s => s.id === sceneId);
        if (step) {
          step.panorama = imgPath;
          fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2));
        }
      }
    } catch (e) {
      console.error('Config update error:', e.message);
    }
  }

  res.json({ success: true, path: imgPath, filename: req.file.filename });
});

// List uploaded images
app.get('/api/images/:location', (req, res) => {
  const loc = (req.params.location || '').replace(/[^a-z]/g, '');
  const dir = path.join(__dirname, 'public', 'images', loc);
  if (!fs.existsSync(dir)) return res.json([]);
  const files = fs.readdirSync(dir)
    .filter(f => /\.(jpg|jpeg|png|webp)$/i.test(f))
    .map(f => ({ name: f, path: `/images/${loc}/${f}` }));
  res.json(files);
});

// ─── Page Routes ───────────────────────────────────────────────────────────
app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'public', 'index.html')));
app.get('/tour', (req, res) => res.sendFile(path.join(__dirname, 'public', 'tour.html')));
app.get('/admin', (req, res) => res.sendFile(path.join(__dirname, 'public', 'admin.html')));

// ─── Start ──────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log('\n╔══════════════════════════════════════════════════╗');
  console.log('║   🕋 MAKKAH MADINA VIRTUAL TOUR - SERVER READY  ║');
  console.log('╠══════════════════════════════════════════════════╣');
  console.log(`║   🌐  http://localhost:${PORT}                       ║`);
  console.log(`║   🕌  Makkah Tour  → /tour?type=makkah           ║`);
  console.log(`║   🌿  Madina Tour  → /tour?type=madina           ║`);
  console.log(`║   ⚙️   Admin Panel → /admin                       ║`);
  console.log('╚══════════════════════════════════════════════════╝\n');
});
