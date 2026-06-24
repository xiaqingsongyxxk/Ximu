import type { Resume, ResumeSection } from '../types/resume';

function makeSection(
  resumeId: string,
  type: string,
  title: string,
  content: any,
  sortOrder: number,
): ResumeSection {
  return {
    id: `${type}-${sortOrder}`,
    resumeId,
    type,
    title,
    sortOrder,
    visible: true,
    content,
    createdAt: new Date(),
    updatedAt: new Date(),
  };
}

export const mockResume: Resume = {
  id: 'mock-1',
  userId: 'user-1',
  title: '张三 - 高级后端开发工程师',
  template: 'classic',
  themeConfig: {
    primaryColor: '#1a1a1a',
    accentColor: '#3b82f6',
    fontFamily: 'Inter',
    fontSize: 'medium',
    lineSpacing: 1.5,
    margin: { top: 20, right: 20, bottom: 20, left: 20 },
    sectionSpacing: 16,
  },
  isDefault: true,
  language: 'zh',
  sections: [
    makeSection('mock-1', 'personal_info', '个人信息', {
      fullName: '张三',
      jobTitle: '高级后端开发工程师',
      age: '28岁',
      gender: '男',
      educationLevel: '本科',
      email: 'zhangsan@example.com',
      phone: '138****8888',
      location: '北京',
    }, 0),
    makeSection('mock-1', 'summary', '个人简介', {
      text: '资深后端开发工程师，8 年以上 Java/Python 开发经验，专注于高并发分布式系统设计与架构优化。精通微服务架构、Kubernetes 容器化部署及 DevOps 自动化流程。',
    }, 1),
    makeSection('mock-1', 'work_experience', '工作经历', {
      items: [
        {
          id: 'work-1',
          company: '某知名互联网科技公司',
          position: '高级后端开发工程师',
          location: '北京',
          startDate: '2022.03',
          endDate: '至今',
          description: '负责核心交易系统架构设计与开发，日均处理请求量过亿。',
          highlights: [
            '设计并实现微服务架构改造，系统吞吐量提升 300%',
            '主导引入 Kubernetes 容器编排，服务部署效率提升 70%',
            '建立自动化测试与 CI/CD 流程，代码发布周期从每周缩短至每日',
          ],
        },
        {
          id: 'work-2',
          company: '某云计算服务商',
          position: '后端开发工程师',
          location: '北京',
          startDate: '2019.07',
          endDate: '2022.02',
          description: '参与企业级云产品后端研发，负责 API 网关与服务治理模块。',
          highlights: [
            '开发 API 网关核心功能，支持日均 5 亿次调用',
            '实现服务限流、熔断、降级等治理能力',
            '优化数据库查询性能，接口响应时间降低 60%',
          ],
        },
      ],
    }, 2),
    makeSection('mock-1', 'education', '教育背景', {
      items: [
        {
          id: 'edu-1',
          institution: '某985高校',
          degree: '本科',
          field: '计算机科学与技术',
          location: '北京',
          startDate: '2015',
          endDate: '2019',
          gpa: '3.8/4.0',
          highlights: [
            '校级优秀毕业生',
            'ACM-ICPC 区域赛铜奖',
            '多次获得校级奖学金',
          ],
        },
      ],
    }, 3),
    makeSection('mock-1', 'projects', '项目经历', {
      items: [
        {
          id: 'proj-1',
          name: '分布式任务调度平台',
          url: '',
          startDate: '2023.06',
          endDate: '2023.12',
          description: '自研企业级分布式任务调度平台，支持复杂依赖编排、任务分片、故障恢复与多集群管理。',
          technologies: ['Java', 'Spring Boot', 'Redis', 'Kafka', 'Kubernetes'],
          highlights: [
            '支持百万级任务并发调度，调度延迟 < 100ms',
            '实现任务状态机与多级重试机制，可用性达 99.99%',
            '提供可视化任务管理与监控告警面板',
          ],
        },
        {
          id: 'proj-2',
          name: '高性能缓存中间件',
          url: '',
          startDate: '2022.08',
          endDate: '2023.03',
          description: '基于 Redis Cluster 封装的高性能缓存中间件，提供自动过期、缓存预热、容量规划等企业级功能。',
          technologies: ['Java', 'Redis', 'Guava', 'Spring Boot'],
          highlights: [
            '缓存命中率优化至 95% 以上',
            '支持缓存冷热数据自动迁移',
            '集成 Spring Cache 开箱即用',
          ],
        },
      ],
    }, 4),
    makeSection('mock-1', 'skills', '技能特长', {
      categories: [
        { id: 'sk-1', name: '后端开发', skills: ['Java', 'Python', 'Go', 'Spring Boot', 'FastAPI', 'Django'] },
        { id: 'sk-2', name: '架构与基础设施', skills: ['微服务架构', 'Kubernetes', 'Docker', 'Kafka', 'Redis', 'MySQL'] },
        { id: 'sk-3', name: 'DevOps', skills: ['CI/CD', 'GitLab CI', 'Jenkins', 'Prometheus', 'Grafana'] },
        { id: 'sk-4', name: '其他', skills: ['系统设计', '性能优化', '数据库调优', '高并发'] },
      ],
    }, 5),
    makeSection('mock-1', 'certifications', '证书&奖项', {
      items: [
        { id: 'cert-1', name: 'AWS Certified Solutions Architect', issuer: 'Amazon', date: '2023' },
        { id: 'cert-2', name: 'CKA 认证', issuer: 'CNCF', date: '2022' },
      ],
    }, 6),
    makeSection('mock-1', 'languages', '语言能力', {
      items: [
        { id: 'lang-1', language: '英语', level: 'CET-6', score: '520分' },
      ],
    }, 7),
  ],
  createdAt: new Date(),
  updatedAt: new Date(),
};
